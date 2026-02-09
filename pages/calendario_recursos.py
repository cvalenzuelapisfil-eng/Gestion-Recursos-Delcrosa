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
# 🔐 SESIÓN
# =====================================================
asegurar_sesion()

if not st.session_state.autenticado:
    st.switch_page("app.py")
    st.stop()

st.set_page_config(page_title="Calendario Enterprise", layout="wide")

if not tiene_permiso(st.session_state.rol, "ver_dashboard"):
    st.error("⛔ Sin permisos")
    st.stop()

st.title("📅 Calendario Enterprise de Recursos")

# =====================================================
# RANGO FECHAS
# =====================================================
hoy = date.today()
c1, c2 = st.columns(2)

with c1:
    inicio = st.date_input("Desde", hoy - timedelta(days=7))
with c2:
    fin = st.date_input("Hasta", hoy + timedelta(days=30))

if inicio > fin:
    st.warning("Rango inválido")
    st.stop()

# =====================================================
# CARGAR DATA
# =====================================================
df = calendario_recursos(inicio, fin)

if df is None or df.empty:
    st.info("Sin datos")
    st.stop()

df.columns = df.columns.str.strip()

# =====================================================
# DETECCIÓN COLUMNAS FLEXIBLE
# =====================================================
def col(posibles):
    for p in posibles:
        for c in df.columns:
            if c.lower() == p.lower():
                return c
    return None

c_inicio = col(["Inicio", "fecha_inicio", "start"])
c_fin = col(["Fin", "fecha_fin", "end"])
c_persona = col(["Personal", "nombre", "empleado"])
c_proyecto = col(["Proyecto", "project"])
c_area = col(["Area", "Área", "department"])

if not all([c_inicio, c_fin, c_persona, c_proyecto]):
    st.error("Columnas obligatorias faltantes")
    st.write(df.columns)
    st.stop()

df = df.rename(columns={
    c_inicio: "Inicio",
    c_fin: "Fin",
    c_persona: "Personal",
    c_proyecto: "Proyecto"
})

if c_area:
    df = df.rename(columns={c_area: "Area"})
else:
    df["Area"] = "General"

df["Inicio"] = pd.to_datetime(df["Inicio"], errors="coerce")
df["Fin"] = pd.to_datetime(df["Fin"], errors="coerce")
df = df.dropna()

# =====================================================
# FILTROS ENTERPRISE
# =====================================================
st.sidebar.header("🎛️ Filtros Enterprise")

f_persona = st.sidebar.multiselect("Personal", sorted(df["Personal"].unique()))
f_area = st.sidebar.multiselect("Área", sorted(df["Area"].unique()))
f_proyecto = st.sidebar.multiselect("Proyecto", sorted(df["Proyecto"].unique()))

if f_persona:
    df = df[df["Personal"].isin(f_persona)]
if f_area:
    df = df[df["Area"].isin(f_area)]
if f_proyecto:
    df = df[df["Proyecto"].isin(f_proyecto)]

if df.empty:
    st.warning("Sin resultados con filtros")
    st.stop()

# =====================================================
# KPI
# =====================================================
k1, k2, k3 = st.columns(3)
k1.metric("Asignaciones", len(df))
k2.metric("Personal activo", df["Personal"].nunique())
k3.metric("Proyectos", df["Proyecto"].nunique())

# =====================================================
# DETECTAR SOBREASIGNACIÓN (POR DÍA)
# =====================================================
df["Conflicto"] = False

for persona in df["Personal"].unique():
    sub = df[df["Personal"] == persona].sort_values("Inicio")

    for i in range(len(sub) - 1):
        if sub.iloc[i + 1]["Inicio"] <= sub.iloc[i]["Fin"]:
            df.loc[sub.index[i], "Conflicto"] = True
            df.loc[sub.index[i + 1], "Conflicto"] = True

# =====================================================
# VISTA
# =====================================================
vista = st.radio("Vista", ["Gantt", "Tabla", "Carga diaria"], horizontal=True)

# ---------------- GANTT ----------------
if vista == "Gantt":
    fig = px.timeline(
        df,
        x_start="Inicio",
        x_end="Fin",
        y="Personal",
        color="Proyecto",
        hover_data=["Proyecto", "Inicio", "Fin", "Conflicto"]
    )
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(height=650)
    st.plotly_chart(fig, use_container_width=True)

# ---------------- TABLA ----------------
elif vista == "Tabla":
    st.dataframe(df, use_container_width=True)

# ---------------- CARGA DIARIA ----------------
else:
    carga = []

    for _, r in df.iterrows():
        dias = pd.date_range(r["Inicio"], r["Fin"])
        for d in dias:
            carga.append([r["Personal"], d, r["Proyecto"]])

    carga_df = pd.DataFrame(carga, columns=["Personal", "Fecha", "Proyecto"])

    heat = carga_df.groupby(["Personal", "Fecha"]).size().reset_index(name="Asignaciones")

    fig = px.density_heatmap(
        heat,
        x="Fecha",
        y="Personal",
        z="Asignaciones"
    )

    st.plotly_chart(fig, use_container_width=True)

# =====================================================
# ALERTA
# =====================================================
if df["Conflicto"].any():
    st.error("⚠️ Sobreasignación detectada")

# =====================================================
# EXPORT EXCEL
# =====================================================
if st.button("⬇️ Exportar Excel"):
    import io
    buf = io.BytesIO()
    df.to_excel(buf, index=False, engine="openpyxl")
    buf.seek(0)
    st.download_button("Descargar", buf, "calendario_enterprise.xlsx")
