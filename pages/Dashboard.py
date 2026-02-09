import streamlit as st
import plotly.express as px
import pandas as pd
from datetime import date, timedelta

from logic import (
    tiene_permiso,
    obtener_personal_dashboard,
    proyectos_gantt_por_persona,
    obtener_alertas_por_persona,
    kpi_proyectos,
    kpi_personal,
    kpi_asignaciones,
    kpi_solapamientos,
    kpi_proyectos_confirmados,
    calendario_recursos
)

st.set_page_config(page_title="Dashboard", layout="wide")

# --- PROTEGER LOGIN ---
if "usuario_id" not in st.session_state:
    st.warning("Debes iniciar sesión")
    st.switch_page("app.py")
    st.stop()

# =====================================================
# 🔐 PROTECCIÓN
# =====================================================
if "usuario" not in st.session_state or not st.session_state.usuario:
    st.error("Sesión no válida")
    st.stop()

if not tiene_permiso(st.session_state.rol, "ver_dashboard"):
    st.error("⛔ No tienes permiso")
    st.stop()

st.title("📊 Dashboard de Gestión")


# =====================================================
# FILTRO POR PERSONA
# =====================================================
st.subheader("🔎 Filtros")

df_personal = obtener_personal_dashboard()
opciones = ["Todos"] + df_personal["nombre"].tolist()

persona_sel = st.selectbox("Filtrar por persona", opciones)

personal_id = None
persona_nombre = None

if persona_sel != "Todos":
    fila = df_personal[df_personal["nombre"] == persona_sel].iloc[0]
    personal_id = int(fila["id"])
    persona_nombre = fila["nombre"]

# 👉 IR A CALENDARIO
if persona_nombre:
    if st.button(f"📅 Ver calendario de {persona_nombre}"):
        st.session_state["filtro_persona"] = persona_nombre
        st.switch_page("calendario.py")

st.divider()


# =====================================================
# KPIs
# =====================================================
col1, col2, col3, col4, col5 = st.columns(5)

activos, cerrados = kpi_proyectos()
total_personal, disponibles, ocupados = kpi_personal()
total_asignaciones = kpi_asignaciones()
solapamientos = kpi_solapamientos()
confirmados, no_confirmados = kpi_proyectos_confirmados()

col1.metric("Proyectos activos", activos)
col2.metric("Personal total", total_personal)
col3.metric("Asignaciones activas", total_asignaciones)
col4.metric("⚠️ Sobreasignaciones", solapamientos)
col5.metric("Proyectos confirmados", confirmados)

st.divider()


# =====================================================
# ALERTAS
# =====================================================
st.subheader("🔔 Alertas")

alertas = obtener_alertas_por_persona(personal_id)

if not alertas:
    st.success("No hay alertas pendientes 🎉")
else:
    for a in alertas:
        st.warning(a)

st.divider()


# =====================================================
# HEATMAP SEMANAL
# =====================================================
st.subheader("🔥 Heatmap semanal de carga")

hoy = date.today()
inicio = hoy - timedelta(weeks=4)
fin = hoy + timedelta(weeks=8)

df_cal = calendario_recursos(inicio, fin)

if persona_nombre:
    df_cal = df_cal[df_cal["Personal"] == persona_nombre]

if not df_cal.empty:

    df_cal["Inicio"] = pd.to_datetime(df_cal["Inicio"])
    df_cal["Fin"] = pd.to_datetime(df_cal["Fin"])

    filas = []
    for _, r in df_cal.iterrows():
        semana = r["Inicio"]
        while semana <= r["Fin"]:
            filas.append({
                "Personal": r["Personal"],
                "Semana": semana.strftime("%Y-%W")
            })
            semana += timedelta(days=7)

    heat = (
        pd.DataFrame(filas)
        .groupby(["Personal", "Semana"])
        .size()
        .reset_index(name="Asignaciones")
    )

    fig_heat = px.density_heatmap(
        heat,
        x="Semana",
        y="Personal",
        z="Asignaciones",
        color_continuous_scale="YlOrRd",
        text_auto=True
    )

    st.plotly_chart(fig_heat, use_container_width=True)

else:
    st.info("No hay datos para el heatmap")

st.divider()


# =====================================================
# GANTT DE PROYECTOS
# =====================================================
st.subheader("📅 Gantt de Proyectos")

df_gantt = proyectos_gantt_por_persona(personal_id)

if df_gantt.empty:
    st.info("No hay proyectos para el filtro seleccionado")
else:

    # Normalizar nombres (tu logic usa minúsculas)
    df_gantt = df_gantt.rename(columns={
        "nombre": "Proyecto",
        "inicio": "Inicio",
        "fin": "Fin",
        "confirmacion": "Confirmacion"
    })

    fig = px.timeline(
        df_gantt,
        x_start="Inicio",
        x_end="Fin",
        y="Proyecto",
        color="Confirmacion"
    )

    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(fig, use_container_width=True)
