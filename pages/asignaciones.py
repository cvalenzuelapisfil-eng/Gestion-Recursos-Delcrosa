import streamlit as st
from datetime import date

from logic import (
    asegurar_sesion,
    tiene_permiso,
    obtener_proyectos,
    obtener_personal,
    asignar_personal,
    hay_solapamiento,
    sugerir_personal,
    registrar_auditoria
)

# -----------------------------------------------------
# 🔐 SEGURIDAD GLOBAL
# -----------------------------------------------------
asegurar_sesion()

if not tiene_permiso(st.session_state.rol, "asignar_personal"):
    st.error("⛔ No tienes permiso para asignar personal")
    st.stop()

# -----------------------------------------------------
# CONFIG
# -----------------------------------------------------
st.set_page_config(page_title="Asignaciones", layout="wide")
st.title("👷 Asignación de Personal a Proyectos")


# -----------------------------------------------------
# PROYECTOS
# -----------------------------------------------------
proyectos = obtener_proyectos()

if not proyectos:
    st.info("No hay proyectos disponibles")
    st.stop()

proyecto = st.selectbox(
    "Proyecto",
    proyectos,
    format_func=lambda x: f"{x[1]} ({'Confirmado' if x[6] else 'No confirmado'})"
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

try:
    sugeridos = sugerir_personal(inicio_proyecto, fin_proyecto)
except Exception as e:
    st.error(f"Error generando sugerencias: {e}")
    sugeridos = None

auto_ids = []

if sugeridos is not None and not sugeridos.empty:
    for _, r in sugeridos.iterrows():
        st.write(f"• {r['nombre']} (carga: {r['carga']})")
        auto_ids.append(int(r["id"]))
else:
    st.info("No hay sugerencias disponibles")

# -----------------------------------------------------
# AUTO ASIGNACIÓN
# -----------------------------------------------------
if auto_ids:
    if st.button("⚡ Auto-asignar sugeridos"):

        try:
            asignar_personal(
                proyecto_id,
                auto_ids,
                inicio_proyecto,
                fin_proyecto,
                st.session_state.usuario_id
            )

            registrar_auditoria(
                st.session_state.usuario_id,
                "ASIGNAR",
                "ASIGNACION",
                proyecto_id,
                f"Auto-asignación de {len(auto_ids)} personas"
            )

            st.success("Asignación automática realizada")
            st.rerun()

        except Exception as e:
            st.error(f"Error en auto-asignación: {e}")


# -----------------------------------------------------
# SELECCIÓN MANUAL
# -----------------------------------------------------
st.divider()
st.subheader("👥 Selección manual de personal")

personal = obtener_personal()

if not personal:
    st.warning("No hay personal registrado")
    st.stop()

personal_map = {p[1]: p[0] for p in personal}
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

for nombre in seleccionados:
    pid = personal_map[nombre]
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

    try:
        asignar_personal(
            proyecto_id,
            ids_seleccionados,
            inicio_proyecto,
            fin_proyecto,
            st.session_state.usuario_id
        )

        registrar_auditoria(
            st.session_state.usuario_id,
            "ASIGNAR",
            "ASIGNACION",
            proyecto_id,
            f"Asignación manual de {len(ids_seleccionados)} personas"
        )

        st.success("Personal asignado correctamente")
        st.rerun()

    except Exception as e:
        st.error(f"Error al asignar personal: {e}")
