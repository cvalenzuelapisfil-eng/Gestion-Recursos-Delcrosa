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
            cur.execute("UPDATE usuarios SET intentos_fallidos=%s, bloqueado_hasta=%s WHERE id=%s",
                        (intentos, bloqueo, user_id))
        else:
            cur.execute("UPDATE usuarios SET intentos_fallidos=%s WHERE id=%s",
                        (intentos, user_id))
        conn.commit()
        cerrar(conn, cur)
        return None

    cur.execute("UPDATE usuarios SET intentos_fallidos=0, bloqueado_hasta=NULL WHERE id=%s",
                (user_id,))
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
# PERSONAL
# =====================================================
def obtener_personal():
    conn = get_connection()
    df = pd.read_sql("""
        SELECT id, nombre, rol, activo
        FROM personal
        ORDER BY nombre
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
# ASIGNACIONES ACTIVAS
# =====================================================
def obtener_asignaciones_activas():
    conn = get_connection()
    df = pd.read_sql("""
        SELECT a.id, p.nombre AS personal, pr.nombre AS proyecto,
               a.inicio, a.fin
        FROM asignaciones a
        JOIN personal p ON a.personal_id = p.id
        JOIN proyectos pr ON a.proyecto_id = pr.id
        WHERE a.activa = TRUE
        ORDER BY a.inicio
    """, conn)
    cerrar(conn)
    return df


# =====================================================
# STUBS COMPATIBILIDAD
# =====================================================
def obtener_carga_personal(*args, **kwargs): return None
def obtener_personal_dashboard(*args, **kwargs): return None
def kpi_proyectos(*args, **kwargs): return 0
def kpi_personal(*args, **kwargs): return 0
def kpi_asignaciones(*args, **kwargs): return 0
def kpi_solapamientos(*args, **kwargs): return 0
def kpi_proyectos_confirmados(*args, **kwargs): return 0
def obtener_alertas_por_persona(*args, **kwargs): return []
def proyectos_gantt_por_persona(*args, **kwargs): return None
def crear_proyecto(*args, **kwargs): pass
def modificar_proyecto(*args, **kwargs): pass
def eliminar_proyecto(*args, **kwargs): pass
def obtener_usuarios(*args, **kwargs): return None
def cambiar_password(*args, **kwargs): pass
def cambiar_rol(*args, **kwargs): pass
def cambiar_estado(*args, **kwargs): pass
def registrar_auditoria(*args, **kwargs): pass
