import streamlit as st
import pandas as pd
import io
from database import get_connection
from logic import tiene_permiso, registrar_auditoria, asegurar_sesion

# --- PROTEGER LOGIN ---
if "usuario_id" not in st.session_state:
    st.warning("Debes iniciar sesión")
    st.switch_page("app.py")
    st.stop()

# =====================================================
# 🔐 SEGURIDAD GLOBAL
# =====================================================
asegurar_sesion()

if not tiene_permiso(st.session_state.rol, "editar_personal"):
    st.error("⛔ No tienes permisos para carga masiva")
    st.stop()

# =====================================================
# CONFIG
# =====================================================
st.set_page_config(page_title="Carga Masiva de Personal", layout="wide")
st.title("📥📤 Carga Masiva de Personal (Excel)")

conn = get_connection()
c = conn.cursor()

# =====================================================
# 📤 EXPORTAR PERSONAL ACTUAL
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
# 📥 IMPORTAR DESDE EXCEL
# =====================================================
st.subheader("📥 Importar / Actualizar desde Excel")

archivo = st.file_uploader("Selecciona archivo Excel", type=["xlsx"])

if archivo:
    try:
        df = pd.read_excel(archivo)

        # Validar columnas
        columnas = {"nombre", "cargo", "area"}
        if not columnas.issubset(df.columns):
            st.error("El Excel debe tener columnas: nombre, cargo, area")
            st.stop()

        # =====================================================
        # LIMPIEZA DE DATOS
        # =====================================================
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
            cargo = fila["cargo"]
            area = fila["area"]

            c.execute("SELECT id FROM personal WHERE nombre=%s", (nombre,))
            existe = c.fetchone()

            if existe:
                actualizar.append((cargo, area, nombre))
            else:
                insertar.append((nombre, cargo, area))

        # =====================================================
        # INSERTAR NUEVOS
        # =====================================================
        if insertar:
            c.executemany("""
                INSERT INTO personal (nombre, cargo, area)
                VALUES (%s, %s, %s)
            """, insertar)

        # =====================================================
        # ACTUALIZAR EXISTENTES
        # =====================================================
        if actualizar:
            c.executemany("""
                UPDATE personal
                SET cargo=%s, area=%s
                WHERE nombre=%s
            """, actualizar)

        conn.commit()

        # =====================================================
        # RESULTADO
        # =====================================================
        st.success(f"""
        ✔️ Carga completada

        • Insertados: {len(insertar)}  
        • Actualizados: {len(actualizar)}
        """)

        registrar_auditoria(
            st.session_state.user_id,
            "CARGA_MASIVA",
            "PERSONAL",
            None,
            f"Insertados={len(insertar)} Actualizados={len(actualizar)}"
        )

    except Exception as e:
        st.error(f"❌ Error en carga masiva: {e}")

    finally:
        c.close()
        conn.close()
