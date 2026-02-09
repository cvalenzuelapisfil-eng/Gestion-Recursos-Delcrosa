import streamlit as st
import pandas as pd
from logic import (
    obtener_proyectos,
    crear_proyecto,
    modificar_proyecto,
    eliminar_proyecto
)

st.set_page_config(page_title="Proyectos", layout="wide")
st.title("📁 Gestión de Proyectos")

# ===============================
# FORMULARIO CREAR PROYECTO
# ===============================
with st.expander("➕ Crear nuevo proyecto"):
    with st.form("form_crear_proyecto"):
        nombre = st.text_input("Nombre del proyecto")
        inicio = st.date_input("Fecha inicio")
        fin = st.date_input("Fecha fin")
        confirmado = st.checkbox("Proyecto confirmado")

        guardar = st.form_submit_button("Guardar proyecto")

        if guardar:
            if not nombre:
                st.error("El nombre es obligatorio")
            else:
                crear_proyecto(
                    nombre,
                    inicio,
                    fin,
                    int(confirmado),
                    st.session_state["usuario"]
                )
                st.success("Proyecto creado correctamente")
                st.rerun()

st.divider()

# ===============================
# LISTADO DE PROYECTOS
# ===============================
st.subheader("📋 Proyectos registrados")

proyectos = obtener_proyectos()

# ✅ VALIDACIÓN CORRECTA
if not proyectos:
    st.info("No hay proyectos registrados")
    st.stop()

# Convertimos a DataFrame SOLO PARA LA VISTA
df = pd.DataFrame(
    proyectos,
    columns=["id", "nombre", "codigo", "estado", "inicio", "fin", "confirmado"]
)

st.dataframe(df, use_container_width=True, hide_index=True)

st.divider()

# ===============================
# MODIFICAR / ELIMINAR
# ===============================
st.subheader("✏️ Modificar / 🗑️ Eliminar proyecto")

proyecto_sel = st.selectbox(
    "Selecciona un proyecto",
    proyectos,
    format_func=lambda p: f"{p[1]} ({p[4]} → {p[5]})"
)

pid, nombre, codigo, estado, inicio, fin, confirmado = proyecto_sel

with st.form("form_modificar"):
    nuevo_nombre = st.text_input("Nombre", nombre)
    nuevo_inicio = st.date_input("Inicio", inicio)
    nuevo_fin = st.date_input("Fin", fin)
    nuevo_confirmado = st.checkbox("Confirmado", bool(confirmado))

    col1, col2 = st.columns(2)

    with col1:
        guardar = st.form_submit_button("💾 Guardar cambios")

    with col2:
        eliminar = st.form_submit_button("🗑️ Eliminar proyecto")

    if guardar:
        modificar_proyecto(
            pid,
            nuevo_nombre,
            nuevo_inicio,
            nuevo_fin,
            int(nuevo_confirmado),
            st.session_state["usuario"]
        )
        st.success("Proyecto actualizado")
        st.rerun()
        
if eliminar:
    eliminar_proyecto(pid)
    st.success("Proyecto eliminado")
    st.rerun()


