import streamlit as st
import plotly.express as px
import pandas as pd
from datetime import date, timedelta

from logic import (
    asegurar_sesion,
    calendario_recursos,
    tiene_permiso
)

# =====================================================
# CONFIG
# =====================================================
st.set_page_config(page_title="Calendario de Recursos", layout="wide")

# =====================================================
# 🔐 SEGURIDAD GLOBAL
# =====================================================
asegurar_sesion()

if not tiene_permiso(st.session_state.rol, "ver_dashboard"):
    st.error("⛔ No tienes permiso para acceder")
    st.stop()

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
# CARGA DE DATOS
# =====================================================
try:
    df = calendario_recursos(inicio, fin)
except Exception as e:
    st.error(f"Error cargando calendario: {e}")
    st.stop()

if df.empty:
    st.info("No hay asignaciones en este rango")
    st.stop()

# Filtro por persona
if persona_filtro:
    df = df[df["Personal"] == persona_filtro]
    if df.empty:
        st.info("No hay asignaciones para esta persona en el rango")
        st.stop()

# Normalizar fechas
df["Inicio"] = pd.to_datetime(df["Inicio"])
df["Fin"] = pd.to_datetime(df["Fin"])

# =====================================================
# DETECTAR SOLAPAMIENTOS (VISUAL)
# =====================================================
df["Conflicto"] = False

for persona in df["Personal"].unique():
    subset = df[df["Personal"] == persona].sort_values("Inicio")

    for i in range(len(subset) - 1):
        actual_fin = subset.iloc[i]["Fin"]
        siguiente_inicio = subset.iloc[i + 1]["Inicio"]

        if siguiente_inicio <= actual_fin:
            df.loc[subset.index[i], "Conflicto"] = True
            df.loc[subset.index[i + 1], "Conflicto"] = True

# =====================================================
# CALENDARIO VISUAL (GANTT)
# =====================================================
fig = px.timeline(
    df,
    x_start="Inicio",
    x_end="Fin",
    y="Personal",
    color="Proyecto",
    hover_data={
        "Proyecto": True,
        "Inicio": True,
        "Fin": True,
        "Conflicto": True
    }
)

fig.update_yaxes(autorange="reversed")
fig.update_layout(height=600)

st.plotly_chart(fig, use_container_width=True)

# =====================================================
# ALERTA DE CONFLICTOS
# =====================================================
if df["Conflicto"].any():
    st.warning("⚠️ Existen solapamientos de asignaciones")

# =====================================================
# LIMPIAR FILTRO
# =====================================================
if persona_filtro:
    if st.button("🔄 Ver todo el personal"):
        st.session_state.pop("filtro_persona", None)
        st.rerun()
