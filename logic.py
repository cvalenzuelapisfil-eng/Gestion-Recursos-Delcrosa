import hashlib
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st
from database import get_connection

# =====================================================
# SESIÓN SEGURA
# =====================================================
def asegurar_sesion():
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False
    if "usuario" not in st.session_state:
        st.session_state["usuario"] = None
    if "rol" not in st.session_state:
        st.session_state["rol"] = "publico"
    if "user_id" not in st.session_state:
        st.session_state["user_id"] = None


# =====================================================
# ROLES
# =====================================================
PERMISOS = {
    "admin": {"asignar_personal"},
    "gestor": {"asignar_personal"},
    "usuario": set()
}

def tiene_permiso(rol, permiso):
    return permiso in PERMISOS.get(rol, set())


# =====================================================
# UTILIDADES
# =====================================================
def cerrar(conn, cur=None):
    try:
        if cur:
            cur.close()
    finally:
        conn.close()


# =====================================================
# PROYECTOS
# =====================================================
def obtener_proyectos():
    conn = get_connection()
    df = pd.read_sql("""
        SELECT id, nombre, inicio, fin, confirmado
        FROM proyectos
        WHERE eliminado = FALSE
        ORDER BY inicio DESC
    """, conn)
    cerrar(conn)
    return df


# =====================================================
# PERSONAL DISPONIBLE
# =====================================================
def obtener_personal_disponible(inicio, fin):
    conn = get_connection()
    df = pd.read_sql("""
        SELECT id, nombre
        FROM personal
        WHERE activo = TRUE
        AND id NOT IN (
            SELECT personal_id
            FROM asignaciones
            WHERE activa = TRUE
            AND inicio <= %s
            AND fin >= %s
        )
        ORDER BY nombre
    """, conn, params=(fin, inicio))
    cerrar(conn)
    return df


# =====================================================
# CARGA PERSONAL (%)
# =====================================================
def obtener_carga_personal(personal_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(*)
        FROM asignaciones
        WHERE personal_id = %s
        AND activa = TRUE
    """, (personal_id,))

    total = cur.fetchone()[0]
    cerrar(conn, cur)

    # Ajusta según tu lógica real
    carga = min(total * 25, 100)
    return carga


# =====================================================
# SOLAPAMIENTO
# =====================================================
def hay_solapamiento(personal_id, inicio, fin):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*)
        FROM asignaciones
        WHERE personal_id = %s
        AND activa = TRUE
        AND inicio <= %s
        AND fin >= %s
    """, (personal_id, fin, inicio))
    existe = cur.fetchone()[0] > 0
    cerrar(conn, cur)
    return existe


# =====================================================
# ASIGNAR PERSONAL
# =====================================================
def asignar_personal(proyecto_id, personal_ids, inicio, fin, usuario=None):
    conn = get_connection()
    cur = conn.cursor()

    for pid in personal_ids:
        cur.execute("""
            INSERT INTO asignaciones (personal_id, proyecto_id, inicio, fin, activa)
            VALUES (%s, %s, %s, %s, TRUE)
        """, (pid, proyecto_id, inicio, fin))

    conn.commit()
    cerrar(conn, cur)


# =====================================================
# MOTOR SUGERENCIA (stub seguro)
# =====================================================
def sugerir_personal(*args, **kwargs):
    return []


# =====================================================
# AUDITORÍA (stub seguro)
# =====================================================
def registrar_auditoria(usuario_id, accion, modulo, objeto_id, descripcion):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO auditoria (usuario_id, accion, modulo, objeto_id, descripcion, fecha)
        VALUES (%s, %s, %s, %s, %s, NOW())
    """, (usuario_id, accion, modulo, objeto_id, descripcion))

    conn.commit()
    cerrar(conn, cur)
