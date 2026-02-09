import streamlit as st
import plotly.express as px
from logic import obtener_gantt

st.set_page_config(page_title="Gantt", layout="wide")
st.title("🗓 Gantt de Asignaciones")

# ======================
# OBTENER DATOS
# ======================
df = obtener_gantt()

# ======================
# VALIDACIÓN CORRECTA
# ======================
if df is None or df.empty:
    st.info("No hay asignaciones aún")
    st.stop()

# ======================
# GANTT
# ======================
fig = px.timeline(
    df,
    x_start="Inicio",
    x_end="Fin",
    y="Tecnico",
    color="Proyecto"
)

fig.update_yaxes(autorange="reversed")
fig.update_layout(
    xaxis_title="Fecha",
    yaxis_title="Técnico"
)

st.plotly_chart(fig, use_container_width=True)
