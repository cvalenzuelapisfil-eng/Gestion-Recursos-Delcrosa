import streamlit as st
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

# =====================================================
# 🔐 SESIÓN GLOBAL
# =====================================================
asegurar_sesion()

if not st.session_state.autenticado:
    st.switch_page("app.py")
    st.stop()

# =====================================================
# 🔐 PERMISOS
# =====================================================
if not tiene_permiso(st.session_state.rol, "asignar_personal"):
    st.error("⛔ No tienes permiso para asignar personal")
    st.stop()

# =====================================================
# CONFIG
# =====================================================
st.set_page_config(page_title="Asignaciones", layout="wide")
st.title("👷 Asignación de Personal a Proyectos")

# =====================================================
# PROYECTOS
# =====================================================
proyectos = obtener_proyectos()

if proyectos.empty:
    st.info("No hay proyectos disponibles")
    st.stop()

proyecto = st.selectbox(
    "Proyecto",
    proyectos.to_dict("records"),
    format_func=lambda x: f"{x['nombre']} ({'Confirmado' if x['confirmado'] else 'No confirmado'})"
)

proyecto_id = proyecto["id"]
inicio_proyecto = proyecto["inicio"]
fin_proyecto = proyecto["fin"]
confirmado = proyecto["confirmado"]

st.info(f"📅 Fechas del proyecto: {inicio_proyecto} → {fin_proyecto}")

# =====================================================
# 🤖 SUGERENCIA AUTOMÁTICA
# =====================================================
st.subheader("🤖 Sugerencia automática")

sugeridos = sugerir_personal(inicio_proyecto, fin_proyecto)
auto_ids = []

if not sugeridos.empty:
    for _, r in sugeridos.iterrows():
        st.write(f"• {r['nombre']} (carga: {r['carga']})")
        auto_ids.append(int(r["id"]))
else:
    st.info("No hay sugerencias disponibles")

# =====================================================
# AUTO-ASIGNACIÓN
# =====================================================
if auto_ids and st.button("⚡ Auto-asignar sugeridos"):
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

# =====================================================
# SELECCIÓN MANUAL
# =====================================================
st.divider()
st.subheader("👥 Selección manual de personal")

personal = obtener_personal()

if personal.empty:
    st.warning("No hay personal registrado")
    st.stop()

personal_map = dict(zip(personal["nombre"], personal["id"]))
nombres = list(personal_map.keys())

seleccionados = st.multiselect("Selecciona personal", nombres)

if not seleccionados:
    st.stop()

ids_seleccionados = [personal_map[n] for n in seleccionados]

# =====================================================
# VALIDACIÓN SOLAPAMIENTOS
# =====================================================
st.subheader("⚠️ Validación de carga")

conflictos = [
    n for n in seleccionados
    if hay_solapamiento(personal_map[n], inicio_proyecto, fin_proyecto)
]

if conflictos:
    st.error("🚨 Personal con asignaciones solapadas")
    for c in conflictos:
        st.write(f"• {c}")

    if confirmado:
        st.warning("Proyecto confirmado → no permitido")
        st.stop()
    else:
        if not st.checkbox("Continuar igualmente"):
            st.stop()

# =====================================================
# CONFIRMAR
# =====================================================
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
