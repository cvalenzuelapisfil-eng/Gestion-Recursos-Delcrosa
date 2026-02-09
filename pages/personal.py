import streamlit as st
import pandas as pd
from database import get_connection

st.set_page_config(
    page_title="Estado y Gestión del Personal",
    layout="wide"
)

st.title("🧑‍💼 Estado y Gestión del Personal")

conn = get_connection()

# =====================================================
# OBTENER PERSONAL + ESTADO REAL
# =====================================================
df = pd.read_sql("""
    SELECT 
        p.id,
        p.nombre,
        p.cargo,
        p.area,
        CASE
            WHEN EXISTS (
                SELECT 1
                FROM asignaciones a
                JOIN proyectos pr ON pr.id = a.proyecto_id
                WHERE a.personal_id = p.id
                AND a.activa = 1
                AND pr.eliminado = 0
                AND a.fin >= CURRENT_DATE
            )
            THEN 'Ocupado'
            ELSE 'Disponible'
        END AS estado
    FROM personal p
    ORDER BY p.nombre
""", conn)

# =====================================================
# TABLA DE ESTADO DEL PERSONAL
# =====================================================
st.subheader("📋 Estado del Personal")

if df.empty:
    st.info("No hay personal registrado")
else:
    tabla = df.copy()
    tabla["Indicador"] = tabla["estado"].apply(
        lambda x: "🟢 Disponible" if x == "Disponible" else "🟡 Ocupado"
    )

    st.dataframe(
        tabla[["nombre", "cargo", "area", "estado", "Indicador"]],
        use_container_width=True,
        hide_index=True
    )

# =====================================================
# EDICIÓN DE PERSONAL
# =====================================================
st.divider()
st.subheader("✏️ Modificar datos del personal")

if not df.empty:
    # Selector de persona
    persona_map = {
        f"{row['nombre']} ({row['cargo']})": row["id"]
        for _, row in df.iterrows()
    }

    seleccion = st.selectbox(
        "Selecciona una persona",
        options=list(persona_map.keys())
    )

    persona_id = persona_map[seleccion]
    persona = df[df["id"] == persona_id].iloc[0]

    with st.form("editar_personal"):
        nombre = st.text_input("Nombre", value=persona["nombre"])
        cargo = st.text_input("Cargo", value=persona["cargo"])
        area = st.text_input("Área", value=persona["area"])

        guardar = st.form_submit_button("💾 Guardar cambios")

        if guardar:
            c = conn.cursor()
            c.execute("""
                UPDATE personal
                SET nombre = ?, cargo = ?, area = ?
                WHERE id = ?
            """, (nombre.strip(), cargo.strip(), area.strip(), persona_id))
            conn.commit()

            st.success("✅ Datos del personal actualizados correctamente")
            st.rerun()

conn.close()

# =====================================================
# NOTA INFORMATIVA
# =====================================================
st.caption(
    "🔎 **Estado del personal:** "
    "Se considera *Ocupado* si tiene al menos una asignación activa "
    "en proyectos no eliminados con fecha vigente."
)
