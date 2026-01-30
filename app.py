import streamlit as st
from database import crear_tablas
from logic import (
    agregar_personal,
    obtener_personal,
    agregar_proyecto,
    obtener_proyectos,
    asignar_personal
)

# Inicializar BD
crear_tablas()

st.set_page_config(page_title="Gestión de Proyectos y Recursos", layout="wide")

st.title("📊 Gestión de Proyectos y Recursos")

# ---------------- PERSONAL ----------------
st.header("👷 Registro de Personal")

with st.form("form_personal"):
    codigo = st.text_input("Código personal")
    nombre = st.text_input("Nombre")
    rol = st.selectbox("Rol", ["Técnico", "Supervisor", "Ingeniero"])
    guardar = st.form_submit_button("Agregar personal")

    if guardar:
        agregar_personal(codigo, nombre, rol)
        st.success("Personal agregado correctamente")

# ---------------- PROYECTOS ----------------
st.header("📁 Registro de Proyectos")

with st.form("form_proyecto"):
    cod_proy = st.text_input("Código del proyecto")
    nom_proy = st.text_input("Nombre del proyecto")
    estado = st.selectbox("Estado", ["Confirmado", "En proceso", "Finalizado"])
    inicio = st.date_input("Fecha inicio")
    fin = st.date_input("Fecha fin")
    guardar_p = st.form_submit_button("Agregar proyecto")

    if guardar_p:
        agregar_proyecto(cod_proy, nom_proy, estado, inicio, fin)
        st.success("Proyecto agregado correctamente")

# ---------------- ASIGNACIONES ----------------
st.header("🔗 Asignar Personal a Proyecto")

personal = obtener_personal()
proyectos = obtener_proyectos()

if personal and proyectos:
    opciones_personal = {
        f"{nombre} ({estado})": pid
        for pid, nombre, estado in personal
    }

    opciones_proyectos = {
        nombre: pid
        for pid, nombre in proyectos
    }

    persona_sel = st.selectbox("Personal", opciones_personal.keys())
    proyecto_sel = st.selectbox("Proyecto", opciones_proyectos.keys())

    if st.button("Asignar"):
        asignar_personal(
            opciones_personal[persona_sel],
            opciones_proyectos[proyecto_sel]
        )
        st.success("Personal asignado correctamente")
else:
    st.info("Debe existir personal y proyectos antes de asignar")

# ---------------- LISTADO ----------------
st.header("📋 Estado del Personal")

for pid, nombre, estado in personal:
    st.write(f"• **{nombre}** → {estado}")

