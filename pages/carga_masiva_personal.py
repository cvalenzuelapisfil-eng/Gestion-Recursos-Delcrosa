import streamlit as st
import pandas as pd
import io
import time
from database import get_connection
from logic import tiene_permiso, registrar_auditoria, asegurar_sesion

# =====================================================
# 🔐 SESIÓN
# =====================================================
asegurar_sesion()

if not st.session_state.autenticado:
    st.switch_page("app.py")
    st.stop()

if not tiene_permiso(st.session_state.rol, "editar_personal"):
    st.error("⛔ Sin permisos")
    st.stop()

# =====================================================
# CONFIG
# =====================================================
st.set_page_config(page_title="Carga Masiva Corporativa", layout="wide")
st.title("🏢 Carga Masiva Corporativa de Personal")

# =====================================================
# NORMALIZADOR COLUMNAS
# =====================================================
MAPEO_COLUMNAS = {
    "nombre": ["nombre", "name", "empleado"],
    "cargo": ["cargo", "puesto", "rol", "position"],
    "area": ["area", "área", "department", "dept"]
}

def normalizar_columnas(df):
    columnas_nuevas = {}
    for col in df.columns:
        c = col.strip().lower()
        for destino, aliases in MAPEO_COLUMNAS.items():
            if c in aliases:
                columnas_nuevas[col] = destino
    df = df.rename(columns=columnas_nuevas)
    return df

# =====================================================
# 📄 PLANTILLA
# =====================================================
st.subheader("📄 Plantilla oficial")

plantilla = pd.DataFrame({
    "nombre": ["Juan Pérez"],
    "cargo": ["Ingeniero"],
    "area": ["Operaciones"]
})

buf = io.BytesIO()
plantilla.to_excel(buf, index=False, engine="openpyxl")
buf.seek(0)

st.download_button("⬇️ Descargar plantilla", buf, "plantilla_personal.xlsx")

st.divider()

# =====================================================
# 📥 CARGA MASIVA PERSONAL
# =====================================================
modo_simulacion = st.checkbox("🧪 Simulación (no guarda cambios)")
archivo = st.file_uploader("Sube Excel Personal", type=["xlsx"])

if archivo:

    df = pd.read_excel(archivo)
    df = normalizar_columnas(df)

    if set(df.columns) != {"nombre", "cargo", "area"}:
        st.error("Columnas no válidas")
        st.stop()

    df["nombre"] = df["nombre"].astype(str).str.strip()
    df["cargo"] = df["cargo"].astype(str).str.strip()
    df["area"] = df["area"].astype(str).str.strip()
    df = df.dropna()
    df = df[df["nombre"] != ""]
    df = df.drop_duplicates("nombre")

    st.subheader("Vista previa")
    st.dataframe(df, use_container_width=True)

    if st.button("🚀 Ejecutar carga personal"):

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT nombre FROM personal")
        existentes = {r[0] for r in cur.fetchall()}

        insertar, actualizar, errores = [], [], []

        for fila in df.itertuples():
            nombre, cargo, area = fila.nombre, fila.cargo, fila.area

            if nombre in existentes:
                actualizar.append((cargo, area, nombre))
            else:
                insertar.append((nombre, cargo, area))

        if not modo_simulacion:

            if insertar:
                cur.executemany(
                    "INSERT INTO personal (nombre, cargo, area) VALUES (%s,%s,%s)",
                    insertar
                )

            if actualizar:
                cur.executemany(
                    "UPDATE personal SET cargo=%s, area=%s WHERE nombre=%s",
                    actualizar
                )

            conn.commit()

            registrar_auditoria(
                st.session_state.user_id,
                "CARGA_MASIVA_CORPORATIVA",
                "PERSONAL",
                None,
                f"Insert={len(insertar)} Update={len(actualizar)}"
            )

        cur.close()
        conn.close()

        st.success("Carga finalizada")
        st.metric("Insertados", len(insertar))
        st.metric("Actualizados", len(actualizar))


# =====================================================
# 🏢 ERP PRO — IMPORTACIÓN TRANSACCIONAL
# =====================================================
st.divider()
st.subheader("🚀 ERP PRO — Importación Empresarial")

modo_simulacion_erp = st.checkbox("🧪 Simulación ERP (no guarda)", key="sim_erp")

archivo_multi = st.file_uploader(
    "Sube Excel ERP (Personal / Proyectos / Asignaciones)",
    type=["xlsx"],
    key="erp_pro"
)

if archivo_multi:

    errores = []
    insertados = 0
    actualizados = 0

    try:
        xls = pd.ExcelFile(archivo_multi)

        conn = get_connection()
        conn.autocommit = False   # 🔴 TRANSACCIÓN
        cur = conn.cursor()

        # ================= PERSONAL =================
        if "Personal" in xls.sheet_names:
            df = pd.read_excel(xls, "Personal")

            for i, r in df.iterrows():
                try:
                    nombre = str(r.get("nombre", "")).strip()
                    cargo = str(r.get("cargo", "")).strip()
                    area = str(r.get("area", "")).strip()

                    if not nombre:
                        errores.append((i, "Nombre vacío"))
                        continue

                    cur.execute("SELECT id FROM personal WHERE nombre=%s", (nombre,))
                    ex = cur.fetchone()

                    if ex:
                        if not modo_simulacion_erp:
                            cur.execute(
                                "UPDATE personal SET cargo=%s, area=%s WHERE nombre=%s",
                                (cargo, area, nombre)
                            )
                        actualizados += 1
                    else:
                        if not modo_simulacion_erp:
                            cur.execute(
                                "INSERT INTO personal (nombre, cargo, area) VALUES (%s,%s,%s)",
                                (nombre, cargo, area)
                            )
                        insertados += 1

                except Exception as e:
                    errores.append((i, str(e)))

        # ================= PROYECTOS =================
        if "Proyectos" in xls.sheet_names:
            df = pd.read_excel(xls, "Proyectos")

            for i, r in df.iterrows():
                try:
                    nombre = str(r.get("nombre", "")).strip()
                    inicio = r.get("inicio")
                    fin = r.get("fin")
                    confirmado = bool(r.get("confirmado", False))

                    if not nombre:
                        errores.append((i, "Proyecto sin nombre"))
                        continue

                    if not modo_simulacion_erp:
                        cur.execute("""
                            INSERT INTO proyectos (nombre, inicio, fin, confirmado, estado, eliminado)
                            VALUES (%s,%s,%s,%s,'Activo',FALSE)
                            ON CONFLICT DO NOTHING
                        """, (nombre, inicio, fin, confirmado))

                    insertados += 1

                except Exception as e:
                    errores.append((i, str(e)))

        # ================= ASIGNACIONES =================
        if "Asignaciones" in xls.sheet_names:
            df = pd.read_excel(xls, "Asignaciones")

            for i, r in df.iterrows():
                try:
                    personal = str(r.get("personal", "")).strip()
                    proyecto = str(r.get("proyecto", "")).strip()
                    inicio = r.get("inicio")
                    fin = r.get("fin")

                    if not personal or not proyecto:
                        errores.append((i, "Asignación incompleta"))
                        continue

                    cur.execute("SELECT id FROM personal WHERE nombre=%s", (personal,))
                    p = cur.fetchone()

                    cur.execute("SELECT id FROM proyectos WHERE nombre=%s", (proyecto,))
                    pr = cur.fetchone()

                    if not p or not pr:
                        errores.append((i, "No existe personal/proyecto"))
                        continue

                    if not modo_simulacion_erp:
                        cur.execute("""
                            INSERT INTO asignaciones (personal_id, proyecto_id, inicio, fin, activa)
                            VALUES (%s,%s,%s,%s,TRUE)
                        """, (p[0], pr[0], inicio, fin))

                    insertados += 1

                except Exception as e:
                    errores.append((i, str(e)))

        # 🔴 COMMIT / ROLLBACK
        if modo_simulacion_erp:
            conn.rollback()
        else:
            conn.commit()

        cur.close()
        conn.close()

        # ================= RESULTADO =================
        st.success("ERP PRO ejecutado")

        c1, c2, c3 = st.columns(3)
        c1.metric("Insertados", insertados)
        c2.metric("Actualizados", actualizados)
        c3.metric("Errores", len(errores))

        # Exportar errores
        if errores:
            df_err = pd.DataFrame(errores, columns=["Fila", "Error"])
            buf = io.BytesIO()
            df_err.to_excel(buf, index=False, engine="openpyxl")
            buf.seek(0)

            st.download_button(
                "⬇️ Descargar errores ERP",
                buf,
                "errores_erp.xlsx"
            )

        registrar_auditoria(
            st.session_state.user_id,
            "ERP_PRO_IMPORT",
            "SISTEMA",
            None,
            f"Insert={insertados} Update={actualizados} Error={len(errores)}"
        )

    except Exception as e:
        st.error(f"Fallo ERP PRO — rollback automático: {e}")

