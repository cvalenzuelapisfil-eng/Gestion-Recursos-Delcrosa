import streamlit as st
from datetime import date

from logic import (
    obtener_proyectos,
    obtener_personal_disponible,
    obtener_personal,
    asignar_personal,
    hay_solapamiento
)

st.set_page_config(page_title="Asignaciones", layout="wide")
st.title("👷 Asignación de Personal a Proyectos")

# =====================================================
# SELECCIÓN DE PROYECTO
# =====================================================
proyectos = obtener_proyectos()

if not proyectos:
    st.info("No hay proyectos disponibles")
    st.stop()

proyecto = st.selectbox(
    "Proyecto",
    proyectos,
    format_func=lambda x: f"{x[1]} ({x[6] and 'Confirmado' or 'No confirmado'})"
)

proyecto_id = proyecto[0]
inicio_proyecto = proyecto[4]
fin_proyecto = proyecto[5]
confirmado = proyecto[6]

st.info(f"📅 Fechas del proyecto: {inicio_proyecto} → {fin_proyecto}")

# =====================================================
# SELECCIÓN DE PERSONAL
# =====================================================
st.subheader("👥 Selección de personal")

personal = obtener_personal()

if not personal:
    st.warning("No hay personal registrado")
    st.stop()

personal_map = {f"{p[1]}": p[0] for p in personal}
nombres = list(personal_map.keys())

seleccionados = st.multiselect(
    "Selecciona personal a asignar",
    nombres
)

if not seleccionados:
    st.stop()

ids_seleccionados = [personal_map[n] for n in seleccionados]

# =====================================================
# ALERTA PREVENTIVA
# =====================================================
st.subheader("⚠️ Validación de carga")

conflictos = []

for pid, nombre in zip(ids_seleccionados, seleccionados):
    if hay_solapamiento(pid, inicio_proyecto, fin_proyecto):
        conflictos.append(nombre)

if conflictos:
    st.error("🚨 Atención: personal con asignaciones solapadas")
    for c in conflictos:
        st.write(f"• {c}")

    if confirmado:
        st.warning(
            "Este proyecto está CONFIRMADO. "
            "No se permite asignar personal ya ocupado."
        )
        st.stop()
    else:
        st.warning(
            "El proyecto NO está confirmado. "
            "Puedes continuar bajo tu responsabilidad."
        )

        continuar = st.checkbox("⚠️ Confirmo que deseo asignar igual")

        if not continuar:
            st.stop()

# =====================================================
# CONFIRMAR ASIGNACIÓN
# =====================================================
if st.button("✅ Asignar personal"):
    asignar_personal(
        proyecto_id,
        ids_seleccionados,
        inicio_proyecto,
        fin_proyecto
    )
    st.success("Personal asignado correctamente")
