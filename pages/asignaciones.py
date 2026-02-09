import streamlit as st
from logic import (
    asegurar_sesion,
    tiene_permiso,
    obtener_proyectos,
    obtener_personal_disponible,
    asignar_personal,
    hay_solapamiento,
    sugerir_personal,
    registrar_auditoria,
    obtener_carga_personal
)

# =====================================================
# 🔐 SESIÓN
# =====================================================
asegurar_sesion()

if not st.session_state.autenticado:
    st.switch_page("app.py")
    st.stop()

if not tiene_permiso(st.session_state.rol, "asignar_personal"):
    st.error("⛔ No tienes permiso")
    st.stop()

# =====================================================
# CONFIG
# =====================================================
st.set_page_config(page_title="ERP ULTRA – Asignaciones", layout="wide")
st.title("🧠 ERP ULTRA – Asignación Inteligente de Personal")

# =====================================================
# PROYECTOS
# =====================================================
proyectos = obtener_proyectos()

if proyectos.empty:
    st.info("No hay proyectos")
    st.stop()

proyecto = st.selectbox(
    "Proyecto",
    proyectos.to_dict("records"),
    format_func=lambda x: f"{x['nombre']} ({'Confirmado' if x['confirmado'] else 'No confirmado'})"
)

proyecto_id = proyecto["id"]
inicio = proyecto["inicio"]
fin = proyecto["fin"]

st.info(f"📅 {inicio} → {fin}")

# =====================================================
# 🤖 MOTOR IA ERP ULTRA
# =====================================================
st.subheader("🤖 Motor Inteligente")

# SOLO PERSONAL DISPONIBLE (filtrado desde la BD → modo ERP real)
personal_libre = obtener_personal_disponible(inicio, fin)
if personal_libre.empty:
    st.warning("No hay personal libre en ese rango")
    st.stop()

# Obtener carga actual (%)
personal_libre["carga"] = personal_libre["id"].apply(obtener_carga_personal)

# Orden inteligente → menor carga primero
personal_optimo = personal_libre.sort_values(by="carga")

st.write("### Personal óptimo disponible")

for _, r in personal_optimo.iterrows():
    color = "🟢" if r["carga"] < 70 else "🟡" if r["carga"] < 90 else "🔴"
    st.write(f"{color} {r['nombre']} → Carga {r['carga']}%")

# =====================================================
# ⚡ AUTO-OPTIMIZACIÓN TOTAL
# =====================================================
st.divider()
st.subheader("⚡ Auto Optimización ULTRA")

cantidad = st.number_input(
    "Cantidad de personal requerido",
    min_value=1,
    max_value=len(personal_optimo),
    value=1
)

if st.button("🚀 Asignación Inteligente ULTRA"):
    seleccion = personal_optimo.head(cantidad)

    ids = seleccion["id"].tolist()

    asignar_personal(
        proyecto_id,
        ids,
        inicio,
        fin,
        st.session_state.user_id
    )

    registrar_auditoria(
        st.session_state.user_id,
        "ASIGNACION_ULTRA",
        "ASIGNACION",
        proyecto_id,
        f"ERP ULTRA asignó {len(ids)} personas automáticamente"
    )

    st.success("Asignación optimizada completada")
    st.rerun()

# =====================================================
# 👤 MODO MANUAL INTELIGENTE
# =====================================================
st.divider()
st.subheader("👤 Selección Manual Inteligente")

mapa = dict(zip(personal_optimo["nombre"], personal_optimo["id"]))

seleccion_manual = st.multiselect(
    "Selecciona personal (ordenado por menor carga)",
    list(mapa.keys())
)

if seleccion_manual:
    ids = [mapa[n] for n in seleccion_manual]

    if st.button("✅ Asignar Manual Inteligente"):
        asignar_personal(
            proyecto_id,
            ids,
            inicio,
            fin,
            st.session_state.user_id
        )

        registrar_auditoria(
            st.session_state.user_id,
            "ASIGNACION_MANUAL_ULTRA",
            "ASIGNACION",
            proyecto_id,
            f"Asignación manual ULTRA de {len(ids)} personas"
        )

        st.success("Asignación manual realizada")
        st.rerun()
