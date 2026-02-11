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
# UTILIDADES
# =====================================================
def cerrar(conn, cur=None):
    try:
        if cur:
            cur.close()
    finally:
        conn.close()


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


# =====================================================
# LOGIN
# =====================================================
MAX_INTENTOS = 5
MINUTOS_BLOQUEO = 10


def validar_usuario(usuario, password):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, usuario, rol, password_hash, activo,
               COALESCE(intentos_fallidos, 0),
               bloqueado_hasta
        FROM usuarios
        WHERE usuario = %s
    """, (usuario,))

    user = cur.fetchone()

    if not user:
        cerrar(conn, cur)
        return None

    user_id, username, rol, stored_hash, activo, intentos, bloqueado_hasta = user

    if not activo:
        cerrar(conn, cur)
        return None

    if bloqueado_hasta and datetime.now() < bloqueado_hasta:
        cerrar(conn, cur)
        return None

    if hash_password(password) != stored_hash:
        intentos += 1

        if intentos >= MAX_INTENTOS:
            bloqueo = datetime.now() + timedelta(minutes=MINUTOS_BLOQUEO)
            cur.execute("""
                UPDATE usuarios
                SET intentos_fallidos=%s, bloqueado_hasta=%s
                WHERE id=%s
            """, (intentos, bloqueo, user_id))
        else:
            cur.execute("""
                UPDATE usuarios
                SET intentos_fallidos=%s
                WHERE id=%s
            """, (intentos, user_id))

        conn.commit()
        cerrar(conn, cur)
        return None

    cur.execute("""
        UPDATE usuarios
        SET intentos_fallidos=0, bloqueado_hasta=NULL
        WHERE id=%s
    """, (user_id,))

    conn.commit()
    cerrar(conn, cur)

    return (user_id, username, rol)


# =====================================================
# ROLES
# =====================================================
PERMISOS = {
    "admin": {
        "ver_dashboard",
        "gestionar_usuarios",
        "crear_proyecto",
        "editar_proyecto",
        "eliminar_proyecto",
        "asignar_personal",
        "editar_personal",
        "ver_auditoria"
    },
    "gestor": {
        "ver_dashboard",
        "crear_proyecto",
        "editar_proyecto",
        "asignar_personal",
        "editar_personal"
    },
    "usuario": {
        "ver_dashboard"
    }
}


def tiene_permiso(rol, permiso):
    return permiso in PERMISOS.get(rol, set())


# =====================================================
# PROYECTOS
# =====================================================
def obtener_proyectos():
    conn = get_connection()
    df = pd.read_sql("""
        SELECT id, nombre, codigo, estado, inicio, fin, confirmado
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
        WHERE id NOT IN (
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
