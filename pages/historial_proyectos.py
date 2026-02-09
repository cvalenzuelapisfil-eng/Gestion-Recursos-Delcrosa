import streamlit as st
import pandas as pd
import io
from datetime import date, timedelta
from database import get_connection
from logic import tiene_permiso

# =====================================================
# 🔐 PROTEGER LOGIN
# =====================================================
if "usuario_id" not in st.session_state or not st.session_state.usuario_id:
    st.warning("Debes iniciar sesión")
    st.switch_page("app.py")
    st.stop()

# =====================================================
# 🔐 VALIDAR SESIÓN
# =====================================================
if "usuario" not in st.session_state or not st.session_state.usuario:
    st.error("Sesión inválida")
    st.stop()

if not tiene_permiso(st.session_state.rol, "ver_auditoria"):
    st.error("⛔ No tienes permisos para ver el historial")
    st.stop()

# =====================================================
# CONFIG
# =====================================================
st.set_page_config(page_title="Historial de Proyectos", layout="wide")
st.title("📜 Historial de Cambios de Proyectos")

conn = get_connection()

# =====================================================
# FILTROS
# =====================================================
st.subheader("🔎 Filtros")

col1, col2, col3, col4 = st.columns(4)

with col1:
    fecha_inicio = st.date_input("Desde", date.today() - timedelta(days=30))

with col2:
    fecha_fin = st.date_input("Hasta", date.today())

with col3:
    usuario_filtro = st.text_input("Usuario")

with col4:
    accion_filtro = st.selectbox(
        "Acción",
        ["Todas", "INSERT", "UPDATE", "DELETE"]
    )

# =====================================================
# QUERY DINÁMICA
# =====================================================
query = """
    SELECT
        ph.fecha,
        p.nombre AS proyecto,
        ph.accion,
        ph.campo,
        ph.valor_anterior,
        ph.valor_nuevo,
        ph.usuario
    FROM proyectos_historial ph
    JOIN proyectos p ON p.id = ph.proyecto_id
    WHERE ph.fecha BETWEEN %s AND %s
"""

params = [fecha_inicio, fecha_fin]

if usuario_filtro:
    query += " AND LOWER(ph.usuario) LIKE LOWER(%s)"
    params.append(f"%{usuario_filtro}%")

if accion_filtro != "Todas":
    query += " AND ph.accion = %s"
    params.append(accion_filtro)

query += " ORDER BY ph.fecha DESC"

df = pd.read_sql(query, conn, params=params)
conn.close()

# =====================================================
# RESULTADO
# =====================================================
if df.empty:
    st.info("No hay historial con esos filtros")
    st.stop()

# =====================================================
# KPIs DE ACTIVIDAD
# =====================================================
st.subheader("📊 Actividad")

col1, col2, col3 = st.columns(3)
col1.metric("Total cambios", len(df))
col2.metric("Usuarios únicos", df["usuario"].nunique())
col3.metric("Proyectos afectados", df["proyecto"].nunique())

st.divider()

# =====================================================
# TABLA
# =====================================================
st.subheader("📋 Detalle")

st.dataframe(
    df,
    use_container_width=True,
    column_config={
        "fecha": "Fecha",
        "proyecto": "Proyecto",
        "accion": "Acción",
        "campo": "Campo",
        "valor_anterior": "Antes",
        "valor_nuevo": "Después",
        "usuario": "Usuario"
    }
)

# =====================================================
# EXPORTAR
# =====================================================
st.divider()
st.subheader("📥 Exportar")

buffer = io.BytesIO()
df.to_excel(buffer, index=False, engine="openpyxl")
buffer.seek(0)

st.download_button(
    "⬇️ Descargar historial en Excel",
    data=buffer,
    file_name="historial_proyectos.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
