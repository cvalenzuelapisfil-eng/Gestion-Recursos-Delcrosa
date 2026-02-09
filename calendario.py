import streamlit as st
import plotly.express as px
import pandas as pd
from logic import obtener_gantt

st.set_page_config(page_title="Calendario de Recursos", layout="wide")
st.title("📆 Calendario de Proyectos y Personal")

df = obtener_gantt()

if df.empty:
    st.info("No hay asignaciones activas")
    st.stop()

df["Evento"] = df["Proyecto"] + " - " + df["Tecnico"]

fig = px.timeline(
    df,
    x_start="Inicio",
    x_end="Fin",
    y="Evento",
    color="Proyecto",
)

fig.update_yaxes(autorange="reversed")
fig.update_layout(
    xaxis_title="Fecha",
    yaxis_title="Asignaciones",
    height=700
)

st.plotly_chart(fig, use_container_width=True)
