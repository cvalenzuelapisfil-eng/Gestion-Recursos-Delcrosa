import streamlit as st
from logic import agregar_personal, listar_personal

st.subheader("👷 Gestión de Personal")

with st.form("form_personal"):
    codigo = st.text_input("Código personal")
    nombre = st.text_input("Nombre")
    rol = st.selectbox("Rol", ["Técnico", "Supervisor", "Ingeniero"])
    disponible = st.checkbox("Disponible", value=True)
    guardar = st.form_submit_button("Agregar personal")

    if guardar:
        agregar_personal(codigo, nombre, rol, disponible)
        st.success("Personal agregado correctamente")

st.markdown("### 📋 Lista de personal")
personal = listar_personal()
st.table(personal)
