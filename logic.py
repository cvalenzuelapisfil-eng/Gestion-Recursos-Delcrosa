import hashlib
import pandas as pd
from datetime import datetime, timedelta
from database import get_connection
import streamlit as st

# =====================================================
# CONFIG SEGURIDAD LOGIN
# =====================================================

MAX_INTENTOS = 5
MINUTOS_BLOQUEO = 10

# =====================================================
# SESIÓN STREAMLIT (ESTABLE)
# =====================================================

def asegurar_sesion():
    if "user_id" not in st.session_state:
        st.session_state.user_id = None

    if "usuario" not in st.session_state:
        st.session_state.usuario = None

    if "rol" not in st.session_state:
        st.session_state.rol = "publico"

    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False


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
# ROLES Y PERMISOS
# =====================================================

   PERMISOS = {
    "admin": {
        "ver_dashboard",
        "gestionar_usuarios",
        "crear_proyecto",
        "editar_proyecto",
        "eliminar_proyecto",
        "asignar_personal",
        "editar_personal",        # 👈 AÑADIR
        "ver_auditoria"           # 👈 AÑADIR
    },
    "gestor": {
        "ver_dashboard",
        "crear_proyecto",
        "editar_proyecto",
        "asignar_personal",
        "editar_personal"         # 👈 OPCIONAL
    },
    "usuario": {
        "ver_dashboard"
    }
}



def tiene_permiso(rol, permiso):
    return permiso in PERMISOS.get(rol, set())


# =====================================================
# AUDITORIA
# =====================================================

def registrar_auditoria(usuario_id, accion, entidad, entidad_id=None, detalle=""):
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO auditoria (usuario_id, accion, entidad, entidad_id, detalle)
            VALUES (%s, %s, %s, %s, %s)
        """, (usuario_id, accion, entidad, entidad_id, detalle))

        conn.commit()
        cerrar(conn, cur)
    except Exception:
        pass


# =====================================================
# LOGIN SEGURO
# =====================================================

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


def crear_proyecto(nombre, inicio, fin, confirmado, usuario=None):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO proyectos (nombre, inicio, fin, confirmado, estado, eliminado)
        VALUES (%s, %s, %s, %s, 'Activo', FALSE)
        RETURNING id
    """, (nombre, inicio, fin, confirmado))

    pid = cur.fetchone()[0]
    conn.commit()
    cerrar(conn, cur)

    if usuario:
        registrar_auditoria(usuario, "CREAR", "PROYECTO", pid, nombre)


def modificar_proyecto(pid, nombre, inicio, fin, confirmado, usuario=None):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE proyectos
        SET nombre=%s, inicio=%s, fin=%s, confirmado=%s
        WHERE id=%s
    """, (nombre, inicio, fin, confirmado, pid))

    conn.commit()
    cerrar(conn, cur)

    if usuario:
        registrar_auditoria(usuario, "EDITAR", "PROYECTO", pid, nombre)


def eliminar_proyecto(pid, usuario=None):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE proyectos
        SET eliminado = TRUE
        WHERE id=%s
    """, (pid,))

    conn.commit()
    cerrar(conn, cur)

    if usuario:
        registrar_auditoria(usuario, "ELIMINAR", "PROYECTO", pid)


# =====================================================
# PERSONAL
# =====================================================

def obtener_personal():
    conn = get_connection()
    df = pd.read_sql("SELECT id, nombre FROM personal ORDER BY nombre", conn)
    cerrar(conn)
    return df


# =====================================================
# ASIGNACIONES
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

    if usuario:
        registrar_auditoria(usuario, "ASIGNAR", "ASIGNACION", proyecto_id)


# =====================================================
# KPIs
# =====================================================

def total_proyectos():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM proyectos WHERE eliminado = FALSE")
    t = cur.fetchone()[0]
    cerrar(conn, cur)
    return t


def total_personal():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM personal")
    t = cur.fetchone()[0]
    cerrar(conn, cur)
    return t


def total_asignaciones_activas():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM asignaciones WHERE activa = TRUE")
    t = cur.fetchone()[0]
    cerrar(conn, cur)
    return t


# =====================================================
# CALENDARIO
# =====================================================

def calendario_recursos(inicio, fin):
    conn = get_connection()
    df = pd.read_sql("""
        SELECT pe.nombre AS Personal, pr.nombre AS Proyecto, a.inicio, a.fin
        FROM asignaciones a
        JOIN personal pe ON pe.id=a.personal_id
        JOIN proyectos pr ON pr.id=a.proyecto_id
        WHERE a.activa=TRUE AND pr.eliminado=FALSE
          AND a.inicio<=%s AND a.fin>=%s
        ORDER BY pe.nombre
    """, conn, params=(fin, inicio))
    cerrar(conn)
    return df
