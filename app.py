import streamlit as st
from database import crear_tablas_y_seed
from logic import obtener_personal, marcar_disponible, marcar_no_disponible

st.set_page_config(
    page_title="Gestión de Recursos",
    layout="wide"
)

# 🔥 ESTO SOLUCIONA TODO
crear_tablas_y_seed()

st.title("👷 Gestión de Personal")

personal = obtener_personal()

st.subheader("Listado General")

for pid, nombre, cargo, area, disponible in personal:
    col1, col2, col3, col4, col5 = st.columns([3,3,3,2,2])

    col1.write(nombre)
    col2.write(cargo)
    col3.write(area)

    if disponible:
        col4.success("Disponible")
        if col5.button("Asignar", key=f"a{pid}"):
            marcar_no_disponible(pid)
            st.experimental_rerun()
    else:
        col4.error("Ocupado")
        if col5.button("Liberar", key=f"l{pid}"):
            marcar_disponible(pid)
            st.experimental_rerun()

