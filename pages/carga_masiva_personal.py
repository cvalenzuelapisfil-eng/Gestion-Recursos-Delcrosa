import streamlit as st
import pandas as pd
import io
from database import get_connection
from logic import tiene_permiso, registrar_auditoria

# =====================================================
# 🔐 SEGURIDAD
# =====================================================
if "usuario" not in st.session_state:
    st.error("Sesión inválida")
    st.stop()

if not tiene_permiso(st.session_state.rol, "editar_personal"):
    st.error("⛔ No tienes permisos para carga masiva")
    st.stop()

usuario = st.session_state.usuario

# =====================================================
# CONFIG
# =====================================================
st.set_page_config(page_title="Carga Masiva de Personal", layout="wide")
st.title("📥📤 Carga Masiva de Personal (Excel)")

conn = get_connection()
c = conn.cursor()

# =====================================================
# EXPORTAR PERSONAL
# =====================================================
st.subheader("📤 Exportar personal actual")

df_personal = pd.read_sql("""
    SELECT nombre, cargo, area
    FROM personal
    ORDER BY nombre
""", conn)

if not df_personal.empty:
    buffer = io.BytesIO()
    df_personal.to_excel(buffer, index=False, engine="openpyxl")
    buffer.seek(0)

    st.download_button(
        "⬇️ Descargar Excel",
        data=buffer,
        file_name="personal.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("No hay personal para exportar")

st.divider()

# =====================================================
# IMPORTAR DESDE EXCEL
# =====================================================
st.subheader("📥 Importar / Actualizar desde Excel")

archivo = st.file_uploader("Selecciona archivo Excel", type=["xlsx"])

if archivo:
    try:
        df = pd.read_excel(archivo)

        columnas = {"nombre", "cargo", "area"}
        if not columnas.issubset(df.columns):
            st.error("El Excel debe tener columnas: nombre, cargo, area")
            st.stop()

        # -------------------------------------------------
        # LIMPIEZA DE DATOS
        # -------------------------------------------------
        df["nombre"] = df["nombre"].astype(str).str.strip()
        df["cargo"] = df["cargo"].astype(str).str.strip()
        df["area"] = df["area"].astype(str).str.strip()

        df = df[df["nombre"] != ""]
        df = df.drop_duplicates(subset=["nombre"], keep="first")

        insertar = []
        actualizar = []
        omitir = []

        for _, fila in df.iterrows():
            nombre = fila["nombre"]
            cargo = fila["cargo"] if fila["cargo"] else None
            area = fila["area"] if fila["area"] else None

            c.execute(
                "SELECT id, cargo, area FROM personal WHERE LOWER(nombre)=LOWER(%s)",
                (nombre,)
            )
            existente = c.fetchone()

            if existente:
                pid, cargo_db, area_db = existente
                cambios = {}

                if cargo != cargo_db:
                    cambios["cargo"] = (cargo_db, cargo)
                if area != area_db:
                    cambios["area"] = (area_db, area)

                if cambios:
                    actualizar.append((pid, nombre, cambios))
                else:
                    omitir.append(nombre)
            else:
                insertar.append((nombre, cargo, area))

        # =====================================================
        # PREVIEW
        # =====================================================
        st.subheader("🧪 Resumen de carga")

        col1, col2, col3 = st.columns(3)
        col1.metric("➕ Nuevos", len(insertar))
        col2.metric("✏️ Actualizar", len(actualizar))
        col3.metric("⚠️ Omitidos", len(omitir))

        if insertar:
            st.write("### Nuevos registros")
            st.dataframe(pd.DataFrame(insertar, columns=["nombre","cargo","area"]))

        if actualizar:
            cambios_preview = []
            for _, nombre, cambios in actualizar:
                for campo, (antes, despues) in cambios.items():
                    cambios_preview.append({
                        "Nombre": nombre,
                        "Campo": campo,
                        "Antes": antes,
                        "Después": despues
                    })
            st.write("### Cambios detectados")
            st.dataframe(pd.DataFrame(cambios_preview))

        # =====================================================
        # CONFIRMAR
        # =====================================================
        if st.button("🚀 Confirmar carga"):

            # INSERTAR
            for nombre, cargo, area in insertar:
                c.execute("""
                    INSERT INTO personal (nombre, cargo, area)
                    VALUES (%s, %s, %s)
                    RETURNING id
                """, (nombre, cargo, area))
                pid = c.fetchone()[0]

                registrar_auditoria(
                    st.session_state.user_id,
                    "INSERT",
                    "PERSONAL",
                    pid,
                    f"Carga masiva: {nombre}"
                )

            # ACTUALIZAR
            for pid, nombre, cambios in actualizar:
                for campo, (antes, despues) in cambios.items():
                    c.execute(
                        f"UPDATE personal SET {campo}=%s WHERE id=%s",
                        (despues, pid)
                    )

                    registrar_auditoria(
                        st.session_state.user_id,
                        "UPDATE",
                        "PERSONAL",
                        pid,
                        f"{campo}: {antes} → {despues}"
                    )

            conn.commit()
            st.success("✅ Carga masiva completada correctamente")
            st.rerun()

    except Exception as e:
        conn.rollback()
        st.error(f"Error al procesar archivo: {e}")

conn.close()
