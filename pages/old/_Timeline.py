import streamlit as st
import pandas as pd
import plotly.express as px
from logic import obtener_gantt

st.set_page_config(page_title="Timeline", layout="wide")
st.title("📆 Timeline de Proyectos")

# ======================
# OBTENER DATOS
# ======================
data = obtener_gantt()

# ======================
# VALIDACIÓN CORRECTA
# ======================
if data is None or data.empty:
    st.info("No hay asignaciones para mostrar")
    st.stop()

# ======================
# TIMELINE
# ======================
fig = px.timeline(
    data,
    x_start="Inicio",
    x_end="Fin",
    y="Tecnico",
    color="Proyecto",
)

fig.update_yaxes(autorange="reversed")
fig.update_layout(
    xaxis_title="Fecha",
    yaxis_title="Técnico"
)

st.plotly_chart(fig, use_container_width=True)
