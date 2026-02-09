import streamlit as st
import pandas as pd
from logic import (
    asegurar_sesion,
    obtener_proyectos,
    crear_proyecto,
    modificar_proyecto,
    eliminar_proyecto,
    tiene_permiso
)

# =====================================================
# 🔐 PROTEGER LOGIN
# =====================================================
if "usuario_id" not in st.session_state or not st.session_state.usuario_id:
    st.warning("Debes iniciar sesión")
    st.switch_page("app.py")
    st.stop()

# =====================================================
# CONFIG
# =====================================================
st.set_page_config(page_title="Proyectos", layout="wide")

# Validar sesión global
asegurar_sesion()

# =====================================================
# BLOQUEO POR PERMISOS
# =====================================================
if not tiene_permiso(st.session_state.rol, "crear_proyecto"):
    st.error("⛔ No tienes permiso para acceder a Proyectos")
    st.stop()

st.title("📁 Gestión de Proyectos")

# =====================================================
# CREAR PROYECTO
# =====================================================
with st.expander("➕ Crear nuevo proyecto"):

    with st.form("form_crear_proyecto"):
        nombre = st.text_input("Nombre del proyecto")
        inicio = st.date_input("Fecha inicio")
        fin = st.date_input("Fecha fin")
        confirmado = st.checkbox("Proyecto confirmado")

        guardar_nuevo = st.form_submit_button("Guardar proyecto")

        if guardar_nuevo:
            if not nombre.strip():
                st.error("El nombre es obligatorio")
            elif inicio > fin:
                st.error("La fecha inicio no puede ser mayor que la fecha fin")
            else:
                crear_proyecto(
                    nombre.strip(),
                    inicio,
                    fin,
                    confirmado,
                    st.session_state.usuario_id
                )
                st.success("Proyecto creado correctamente")
                st.rerun()

st.divider()

# =====================================================
# LISTADO
# =====================================================
st.subheader("📋 Proyectos registrados")

df = obtener_proyectos()

if df.empty:
    st.info("No hay proyectos registrados")
    st.stop()

st.dataframe(df, use_container_width=True, hide_index=True)

st.divider()

# =====================================================
# EDITAR / ELIMINAR
# =====================================================
st.subheader("✏️ Modificar / 🗑️ Eliminar proyecto")

fila = st.selectbox(
    "Selecciona un proyecto",
    df.itertuples(index=False),
    format_func=lambda p: f"{p.nombre} ({p.inicio} → {p.fin})"
)

pid = fila.id

with st.form("form_modificar"):
    nuevo_nombre = st.text_input("Nombre", fila.nombre)
    nuevo_inicio = st.date_input("Inicio", fila.inicio)
    nuevo_fin = st.date_input("Fin", fila.fin)
    nuevo_confirmado = st.checkbox("Confirmado", fila.confirmado)

    col1, col2 = st.columns(2)

    with col1:
        guardar = st.form_submit_button("💾 Guardar cambios")

    with col2:
        eliminar = st.form_submit_button("🗑️ Eliminar proyecto")

# =====================================================
# GUARDAR CAMBIOS
# =====================================================
if guardar:
    if not tiene_permiso(st.session_state.rol, "editar_proyecto"):
        st.error("⛔ No tienes permiso para editar")
        st.stop()

    if not nuevo_nombre.strip():
        st.error("El nombre no puede estar vacío")
        st.stop()

    if nuevo_inicio > nuevo_fin:
        st.error("La fecha inicio no puede ser mayor que la fecha fin")
        st.stop()

    modificar_proyecto(
        pid,
        nuevo_nombre.strip(),
        nuevo_inicio,
        nuevo_fin,
        nuevo_confirmado,
        st.session_state.usuario_id
    )
    st.success("Proyecto actualizado")
    st.rerun()

# =====================================================
# ELIMINAR
# =====================================================
if eliminar:
    if not tiene_permiso(st.session_state.rol, "eliminar_proyecto"):
        st.error("⛔ Solo administrador puede eliminar")
        st.stop()

    eliminar_proyecto(pid, st.session_state.usuario_id)
    st.success("Proyecto eliminado")
    st.rerun()
