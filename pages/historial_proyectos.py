import streamlit as st
import pandas as pd
from database import get_connection

st.set_page_config(page_title="Historial de Proyectos", layout="wide")
st.title("📜 Historial de Cambios de Proyectos")

conn = get_connection()

df = pd.read_sql("""
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
    ORDER BY ph.fecha DESC
""", conn)

conn.close()

if df.empty:
    st.info("No hay historial registrado aún")
else:
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
