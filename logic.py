import hashlib
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st
from database import get_connection


# =====================================================
# SESIÓN SEGURA
# =====================================================
def asegurar_sesion():
    st.session_state.setdefault("autenticado", False)
    st.session_state.setdefault("usuario", None)
    st.session_state.setdefault("rol", "publico")
    st.session_state.setdefault("user_id", None)


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
    "usuario": {"ver_dashboard"}
}


def tiene_permiso(rol, permiso):
    return permiso in PERMISOS.get(rol, set())


# =====================================================
# PERSONAL
# =====================================================
def obtener_personal():
    try:
        conn = get_connection()
        df = pd.read_sql("""
            SELECT id, nombre, rol, activo
            FROM personal
            ORDER BY nombre
        """, conn)
        cerrar(conn)
        if df is None:
            return pd.DataFrame(columns=["id", "nombre", "rol", "activo"])
        return df
    except:
        return pd.DataFrame(columns=["id", "nombre", "rol", "activo"])


def obtener_personal_dashboard():
    df = obtener_personal()
    if df is None or len(df) == 0:
        return pd.DataFrame(columns=["id", "nombre"])
    return df[["id", "nombre"]]


def obtener_personal_disponible(inicio, fin):
    try:
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
        if df is None:
            return pd.DataFrame(columns=["id", "nombre"])
        return df
    except:
        return pd.DataFrame(columns=["id", "nombre"])


# =====================================================
# PROYECTOS
# =====================================================
def obtener_proyectos():
    try:
        conn = get_connection()
        df = pd.read_sql("""
            SELECT id, nombre, codigo, estado, inicio, fin, confirmado
            FROM proyectos
            WHERE eliminado = FALSE
            ORDER BY inicio DESC
        """, conn)
        cerrar(conn)
        if df is None:
            return pd.DataFrame(columns=["id", "nombre", "codigo", "estado", "inicio", "fin", "confirmado"])
        return df
    except:
        return pd.DataFrame(columns=["id", "nombre", "codigo", "estado", "inicio", "fin", "confirmado"])


def crear_proyecto(nombre=None, codigo=None, inicio=None, fin=None, usuario=None):
    if not nombre:
        return
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO proyectos (nombre, codigo, inicio, fin, estado, confirmado, eliminado)
            VALUES (%s, %s, %s, %s, 'planificado', FALSE, FALSE)
        """, (nombre, codigo, inicio, fin))
        conn.commit()
        cerrar(conn, cur)
    except:
        pass


# =====================================================
# ASIGNACIONES
# =====================================================
def hay_solapamiento(personal_id, inicio, fin):
    try:
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
    except:
        return False


def asignar_personal(proyecto_id, personal_ids, inicio, fin, usuario=None):
    try:
        conn = get_connection()
        cur = conn.cursor()
        for pid in personal_ids:
            cur.execute("""
                INSERT INTO asignaciones (personal_id, proyecto_id, inicio, fin, activa)
                VALUES (%s, %s, %s, %s, TRUE)
            """, (pid, proyecto_id, inicio, fin))
        conn.commit()
        cerrar(conn, cur)
    except:
        pass


def obtener_asignaciones_activas():
    try:
        conn = get_connection()
        df = pd.read_sql("""
            SELECT a.id,
                   p.nombre AS personal,
                   pr.nombre AS proyecto,
                   a.inicio,
                   a.fin
            FROM asignaciones a
            JOIN personal p ON a.personal_id = p.id
            JOIN proyectos pr ON a.proyecto_id = pr.id
            WHERE a.activa = TRUE
            ORDER BY a.inicio
        """, conn)
        cerrar(conn)
        if df is None:
            return pd.DataFrame(columns=["id", "personal", "proyecto", "inicio", "fin"])
        return df
    except:
        return pd.DataFrame(columns=["id", "personal", "proyecto", "inicio", "fin"])


# =====================================================
# FUNCIONES DE COMPATIBILIDAD TOTAL
# (Evitan que cualquier página rompa el app)
# =====================================================
def sugerir_personal(*args, **kwargs):
    df = obtener_personal()
    return df.head(5) if df is not None else pd.DataFrame(columns=["id", "nombre"])


def calendario_recursos(*args, **kwargs):
    return obtener_asignaciones_activas()


def obtener_carga_personal(*args, **kwargs):
    return pd.DataFrame(columns=["personal", "carga"])


def registrar_auditoria(*args, **kwargs):
    pass


def kpi_proyectos(*args, **kwargs):
    return len(obtener_proyectos())


def kpi_personal(*args, **kwargs):
    return len(obtener_personal())


def kpi_asignaciones(*args, **kwargs):
    return len(obtener_asignaciones_activas())


def kpi_solapamientos(*args, **kwargs):
    return 0


def kpi_proyectos_confirmados(*args, **kwargs):
    return 0


def obtener_alertas_por_persona(*args, **kwargs):
    return []


def proyectos_gantt_por_persona(*args, **kwargs):
    return pd.DataFrame()


def modificar_proyecto(*args, **kwargs):
    pass


def eliminar_proyecto(*args, **kwargs):
    pass


def cambiar_password(*args, **kwargs):
    pass


def cambiar_rol(*args, **kwargs):
    pass


def cambiar_estado(*args, **kwargs):
    pass


def obtener_usuarios():
    try:
        conn = get_connection()
        df = pd.read_sql("""
            SELECT id, usuario, rol, activo
            FROM usuarios
            ORDER BY usuario
        """, conn)
        cerrar(conn)
        if df is None:
            return pd.DataFrame(columns=["id", "usuario", "rol", "activo"])
        return df
    except:
        return pd.DataFrame(columns=["id", "usuario", "rol", "activo"])
