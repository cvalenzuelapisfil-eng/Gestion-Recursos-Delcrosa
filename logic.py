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
# ASEGURAR SESSION STATE (GLOBAL)
# =====================================================
def asegurar_sesion():
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False

    if "usuario" not in st.session_state:
        st.session_state.usuario = None

    if "rol" not in st.session_state:
        st.session_state.rol = "publico"

    if "user_id" not in st.session_state:
        st.session_state.user_id = None

# =====================================================
# DISPONIBILIDAD Y VALIDACIONES
# =====================================================

def hay_solapamiento(personal_id, inicio, fin):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(*)
        FROM asignaciones a
        JOIN proyectos p ON p.id = a.proyecto_id
        WHERE a.personal_id = %s
          AND a.activa = TRUE
          AND p.eliminado = FALSE
          AND a.inicio <= %s
          AND a.fin >= %s
    """, (personal_id, fin, inicio))

    count = cur.fetchone()[0]
    cerrar(conn, cur)

    return count > 0


def obtener_personal_disponible(inicio, fin):
    conn = get_connection()

    df = pd.read_sql("""
        SELECT p.id, p.nombre
        FROM personal p
        WHERE NOT EXISTS (
            SELECT 1
            FROM asignaciones a
            JOIN proyectos pr ON pr.id = a.proyecto_id
            WHERE a.personal_id = p.id
              AND a.activa = TRUE
              AND pr.eliminado = FALSE
              AND a.inicio <= %s
              AND a.fin >= %s
        )
        ORDER BY p.nombre
    """, conn, params=(fin, inicio))

    cerrar(conn)
    return df


def sugerir_personal(inicio, fin):
    conn = get_connection()

    df = pd.read_sql("""
        SELECT p.id, p.nombre, COUNT(a.id) AS carga
        FROM personal p
        LEFT JOIN asignaciones a
            ON a.personal_id = p.id
           AND a.activa = TRUE
           AND a.inicio <= %s
           AND a.fin >= %s
        GROUP BY p.id, p.nombre
        ORDER BY carga ASC, p.nombre
        LIMIT 5
    """, conn, params=(fin, inicio))

    cerrar(conn)
    return df

# =====================================================
# DASHBOARD EXTRA
# =====================================================

def obtener_personal_dashboard():
    conn = get_connection()
    df = pd.read_sql("SELECT id, nombre FROM personal ORDER BY nombre", conn)
    cerrar(conn)
    return df


def proyectos_gantt_por_persona(personal_id=None):
    conn = get_connection()

    if personal_id:
        df = pd.read_sql("""
            SELECT pr.nombre, a.inicio, a.fin, pr.confirmado
            FROM asignaciones a
            JOIN proyectos pr ON pr.id = a.proyecto_id
            WHERE a.personal_id = %s
              AND a.activa = TRUE
              AND pr.eliminado = FALSE
        """, conn, params=(personal_id,))
    else:
        df = pd.read_sql("""
            SELECT pr.nombre, a.inicio, a.fin, pr.confirmado
            FROM asignaciones a
            JOIN proyectos pr ON pr.id = a.proyecto_id
            WHERE a.activa = TRUE
              AND pr.eliminado = FALSE
        """, conn)

    cerrar(conn)
    return df


def obtener_alertas_por_persona(personal_id=None):
    conn = get_connection()

    if personal_id:
        df = pd.read_sql("""
            SELECT COUNT(*) AS conflictos
            FROM asignaciones
            WHERE personal_id = %s
              AND activa = TRUE
        """, conn, params=(personal_id,))
    else:
        df = pd.read_sql("""
            SELECT COUNT(*) AS conflictos
            FROM asignaciones
            WHERE activa = TRUE
        """, conn)

    cerrar(conn)

    if df.iloc[0]["conflictos"] > 20:
        return ["Alta carga de asignaciones"]
    return []


def kpi_proyectos():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM proyectos WHERE eliminado=FALSE AND estado='Activo'")
    activos = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM proyectos WHERE eliminado=FALSE AND estado='Cerrado'")
    cerrados = cur.fetchone()[0]
    cerrar(conn, cur)
    return activos, cerrados


def kpi_personal():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM personal")
    total = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(DISTINCT personal_id)
        FROM asignaciones
        WHERE activa=TRUE
    """)
    ocupados = cur.fetchone()[0]

    disponibles = total - ocupados
    cerrar(conn, cur)
    return total, disponibles, ocupados


def kpi_asignaciones():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM asignaciones WHERE activa=TRUE")
    total = cur.fetchone()[0]
    cerrar(conn, cur)
    return total


def kpi_solapamientos():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*)
        FROM asignaciones a1
        JOIN asignaciones a2
          ON a1.personal_id = a2.personal_id
         AND a1.id <> a2.id
         AND a1.activa = TRUE
         AND a2.activa = TRUE
         AND (a1.inicio, a1.fin) OVERLAPS (a2.inicio, a2.fin)
    """)
    total = cur.fetchone()[0]
    cerrar(conn, cur)
    return total


def kpi_proyectos_confirmados():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM proyectos WHERE confirmado=TRUE AND eliminado=FALSE")
    confirmados = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM proyectos WHERE confirmado=FALSE AND eliminado=FALSE")
    no_confirmados = cur.fetchone()[0]

    cerrar(conn, cur)
    return confirmados, no_confirmados



# =====================================================
# ASIGNACIONES - GESTIÓN COMPLETA
# =====================================================

def obtener_asignaciones():
    conn = get_connection()
    df = pd.read_sql("""
        SELECT 
            a.id,
            pe.nombre AS personal,
            pr.nombre AS proyecto,
            a.inicio,
            a.fin,
            a.activa
        FROM asignaciones a
        JOIN personal pe ON pe.id = a.personal_id
        JOIN proyectos pr ON pr.id = a.proyecto_id
        WHERE pr.eliminado = FALSE
        ORDER BY a.inicio DESC
    """, conn)
    cerrar(conn)
    return df


def eliminar_asignacion(asignacion_id, usuario=None):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE asignaciones
        SET activa = FALSE
        WHERE id = %s
    """, (asignacion_id,))

    conn.commit()
    cerrar(conn, cur)

    if usuario:
        registrar_auditoria(usuario, "ELIMINAR", "ASIGNACION", asignacion_id)


def modificar_asignacion(asignacion_id, inicio, fin, usuario=None):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE asignaciones
        SET inicio=%s, fin=%s
        WHERE id=%s
    """, (inicio, fin, asignacion_id))

    conn.commit()
    cerrar(conn, cur)

    if usuario:
        registrar_auditoria(usuario, "EDITAR", "ASIGNACION", asignacion_id)


def detectar_solapamientos(personal_id, inicio, fin):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(*)
        FROM asignaciones
        WHERE personal_id = %s
          AND activa = TRUE
          AND (inicio, fin) OVERLAPS (%s, %s)
    """, (personal_id, inicio, fin))

    conflictos = cur.fetchone()[0]
    cerrar(conn, cur)

    return conflictos > 0

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
# USUARIOS
# =====================================================

def obtener_usuarios():
    conn = get_connection()
    df = pd.read_sql("""
        SELECT id, usuario, rol, activo
        FROM usuarios
        ORDER BY usuario
    """, conn)
    cerrar(conn)
    return df


def crear_usuario(usuario, password, rol):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO usuarios (usuario, password_hash, rol, activo)
        VALUES (%s, %s, %s, TRUE)
    """, (usuario, hash_password(password), rol))

    conn.commit()
    cerrar(conn, cur)


def cambiar_password(user_id, nueva_password):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE usuarios
        SET password_hash=%s
        WHERE id=%s
    """, (hash_password(nueva_password), user_id))

    conn.commit()
    cerrar(conn, cur)


def cambiar_rol(user_id, nuevo_rol):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE usuarios
        SET rol=%s
        WHERE id=%s
    """, (nuevo_rol, user_id))

    conn.commit()
    cerrar(conn, cur)


def cambiar_estado(user_id, activo):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE usuarios
        SET activo=%s
        WHERE id=%s
    """, (activo, user_id))

    conn.commit()
    cerrar(conn, cur)


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
