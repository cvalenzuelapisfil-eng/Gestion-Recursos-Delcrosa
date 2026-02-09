import streamlit as st
from datetime import date

from logic import (
    tiene_permiso,
    obtener_proyectos,
    obtener_personal_disponible,
    obtener_personal,
    asignar_personal,
    hay_solapamiento,
    sugerir_personal,
    registrar_auditoria
)

# -----------------------------------------------------
# 🔐 SEGURIDAD
# -----------------------------------------------------
if "usuario" not in st.session_state or not st.session_state.usuario:
    st.error("Sesión no válida")
    st.stop()

if not tiene_permiso(st.session_state.rol, "asignar_personal"):
    st.error("⛔ No tienes permiso para asignar personal")
    st.stop()

# -----------------------------------------------------
# CONFIG
# -----------------------------------------------------
st.set_page_config(page_title="Asignaciones", layout="wide")
st.title("👷 Asignación de Personal a Proyectos")


# -----------------------------------------------------
# SELECCIÓN DE PROYECTO
# -----------------------------------------------------
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


# -----------------------------------------------------
# 🤖 SUGERENCIA AUTOMÁTICA
# -----------------------------------------------------
st.subheader("🤖 Sugerencia automática")

sugeridos = sugerir_personal(inicio_proyecto, fin_proyecto)

auto_ids = []

if not sugeridos.empty:
    for _, r in sugeridos.iterrows():
        st.write(f"• {r['nombre']} (carga: {r['carga']})")
        auto_ids.append(int(r["id"]))
else:
    st.info("No hay sugerencias disponibles")

# AUTO-ASIGNAR
if auto_ids:
    if st.button("⚡ Auto-asignar sugeridos"):

        asignar_personal(
            proyecto_id,
            auto_ids,
            inicio_proyecto,
            fin_proyecto,
            st.session_state.user_id
        )

        registrar_auditoria(
            st.session_state.user_id,
            "ASIGNAR",
            "ASIGNACION",
            proyecto_id,
            f"Auto-asignación de {len(auto_ids)} personas"
        )

        st.success("Asignación automática realizada")
        st.rerun()


# -----------------------------------------------------
# SELECCIÓN MANUAL
# -----------------------------------------------------
st.divider()
st.subheader("👥 Selección manual de personal")

personal = obtener_personal()

if not personal:
    st.warning("No hay personal registrado")
    st.stop()

# Evitar duplicados
personal_map = {f"{p[1]}": p[0] for p in personal}
nombres = list(personal_map.keys())

seleccionados = st.multiselect(
    "Selecciona personal a asignar",
    nombres
)

if not seleccionados:
    st.stop()

ids_seleccionados = [personal_map[n] for n in seleccionados]


# -----------------------------------------------------
# VALIDACIÓN DE CARGA
# -----------------------------------------------------
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


# -----------------------------------------------------
# CONFIRMAR ASIGNACIÓN MANUAL
# -----------------------------------------------------
if st.button("✅ Asignar personal seleccionado"):

    asignar_personal(
        proyecto_id,
        ids_seleccionados,
        inicio_proyecto,
        fin_proyecto,
        st.session_state.user_id
    )

    registrar_auditoria(
        st.session_state.user_id,
        "ASIGNAR",
        "ASIGNACION",
        proyecto_id,
        f"Asignación manual de {len(ids_seleccionados)} personas"
    )

    st.success("Personal asignado correctamente")
    st.rerun()
