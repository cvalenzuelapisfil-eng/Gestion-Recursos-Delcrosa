import streamlit as st
import pandas as pd
import io
from database import get_connection

st.set_page_config(page_title="Carga Masiva de Personal", layout="wide")
st.title("📥📤 Carga Masiva de Personal (Excel)")

usuario = st.session_state.get("usuario", "sistema")

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

archivo = st.file_uploader(
    "Selecciona archivo Excel",
    type=["xlsx"]
)

if archivo:
    try:
        df = pd.read_excel(archivo)

        columnas = {"nombre", "cargo", "area"}
        if not columnas.issubset(df.columns):
            st.error("El Excel debe tener las columnas: nombre, cargo, area")
            st.stop()

        df["nombre"] = df["nombre"].astype(str).str.strip()

        insertar = []
        actualizar = []
        omitir = []

        for _, fila in df.iterrows():
            nombre = fila["nombre"]

            if not nombre:
                omitir.append(fila)
                continue

            cargo = None if pd.isna(fila["cargo"]) else str(fila["cargo"]).strip()
            area = None if pd.isna(fila["area"]) else str(fila["area"]).strip()

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
                    omitir.append(fila)
            else:
                insertar.append((nombre, cargo, area))

        # =====================================================
        # RESUMEN PREVIO
        # =====================================================
        st.subheader("🧪 Resumen de carga")

        col1, col2, col3 = st.columns(3)
        col1.metric("➕ Nuevos", len(insertar))
        col2.metric("✏️ Actualizar", len(actualizar))
        col3.metric("⚠️ Omitidos", len(omitir))

        if st.button("🚀 Confirmar carga"):
            # INSERTAR
            for nombre, cargo, area in insertar:
                c.execute("""
                    INSERT INTO personal (nombre, cargo, area)
                    VALUES (%s, %s, %s)
                """, (nombre, cargo, area))

                pid = c.lastrowid
                c.execute("""
                    INSERT INTO personal_historial
                    (personal_id, accion, campo, valor_nuevo, usuario)
                    VALUES (%s, 'CARGA_MASIVA', 'registro', %s, %s)
                """, (pid, nombre, usuario))

            # ACTUALIZAR
            for pid, nombre, cambios in actualizar:
                for campo, (antes, despues) in cambios.items():
                    c.execute(
                        f"UPDATE personal SET {campo}=%s WHERE id=%s",
                        (despues, pid)
                    )
                    c.execute("""
                        INSERT INTO personal_historial
                        (personal_id, accion, campo, valor_anterior, valor_nuevo, usuario)
                        VALUES (%s, 'CARGA_MASIVA', %s, %s, %s, %s)
                    """, (pid, campo, antes, despues, usuario))

            conn.commit()
            st.success("✅ Carga masiva completada correctamente")

    except Exception as e:
        st.error(f"Error al procesar archivo: {e}")

conn.close()
