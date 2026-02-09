import streamlit as st
import plotly.express as px
from datetime import date, timedelta
from logic import calendario_recursos

st.set_page_config(page_title="Calendario de Recursos", layout="wide")
st.title("📅 Calendario de Recursos")

# =====================================================
# LEER FILTRO DESDE DASHBOARD
# =====================================================
persona_filtro = st.session_state.get("filtro_persona")

if persona_filtro:
    st.info(f"Mostrando calendario de: **{persona_filtro}**")

# =====================================================
# RANGO DE FECHAS
# =====================================================
hoy = date.today()

col1, col2 = st.columns(2)
with col1:
    inicio = st.date_input("Desde", hoy - timedelta(days=7))
with col2:
    fin = st.date_input("Hasta", hoy + timedelta(days=30))

if inicio > fin:
    st.warning("La fecha inicio no puede ser mayor que la fecha fin")
    st.stop()

# =====================================================
# DATOS
# =====================================================
df = calendario_recursos(inicio, fin)

if persona_filtro:
    df = df[df["Personal"] == persona_filtro]

if df.empty:
    st.info("No hay asignaciones en este rango")
    st.stop()

# =====================================================
# CALENDARIO VISUAL
# =====================================================
fig = px.timeline(
    df,
    x_start="Inicio",
    x_end="Fin",
    y="Personal",
    color="Proyecto",
    hover_data=["Proyecto", "Inicio", "Fin"]
)

fig.update_yaxes(autorange="reversed")
fig.update_layout(height=600)

st.plotly_chart(fig, use_container_width=True)

# =====================================================
# LIMPIAR FILTRO (OPCIONAL)
# =====================================================
if st.button("🔄 Ver todo el personal"):
    st.session_state.pop("filtro_persona", None)
    st.rerun()

