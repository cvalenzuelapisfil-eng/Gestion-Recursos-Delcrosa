import hashlib
import pandas as pd
from datetime import datetime, timedelta
from database import get_connection


# =====================================================
# CONFIG SEGURIDAD LOGIN (AÑADIDO)
# =====================================================

MAX_INTENTOS = 5
MINUTOS_BLOQUEO = 10


# =====================================================
# VALIDACIÓN DE SOLAPAMIENTO
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

    existe = cur.fetchone()[0] > 0
    cerrar(conn, cur)
    return existe


# =====================================================
# UTILIDADES
# =====================================================

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def cerrar(conn, cur=None):
    try:
        if cur:
            cur.close()
    finally:
        conn.close()


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
# ROLES Y PERMISOS
# =====================================================

PERMISOS = {
    "admin": {
        "ver_dashboard",
        "gestionar_usuarios",
        "crear_proyecto",
        "editar_proyecto",
        "eliminar_proyecto",
        "asignar_personal"
    },
    "gestor": {
        "ver_dashboard",
        "crear_proyecto",
        "editar_proyecto",
        "asignar_personal"
    },
    "usuario": {
        "ver_dashboard"
    }
}


def tiene_permiso(rol, permiso):
    return permiso in PERMISOS.get(rol, set())


# =====================================================
# LOGIN (MODIFICADO CON SEGURIDAD)
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

    # Usuario inactivo
    if not activo:
        cerrar(conn, cur)
        return None

    # Cuenta bloqueada temporalmente
    if bloqueado_hasta and datetime.now() < bloqueado_hasta:
        cerrar(conn, cur)
        return None

    # Password incorrecto
    if hash_password(password) != stored_hash:
        intentos += 1

        if intentos >= MAX_INTENTOS:
            bloqueo = datetime.now() + timedelta(minutes=MINUTOS_BLOQUEO)

            cur.execute("""
                UPDATE usuarios
                SET intentos_fallidos = %s,
                    bloqueado_hasta = %s
                WHERE id = %s
            """, (intentos, bloqueo, user_id))
        else:
            cur.execute("""
                UPDATE usuarios
                SET intentos_fallidos = %s
                WHERE id = %s
            """, (intentos, user_id))

        conn.commit()
        cerrar(conn, cur)
        return None

    # LOGIN CORRECTO → reset intentos
    cur.execute("""
        UPDATE usuarios
        SET intentos_fallidos = 0,
            bloqueado_hasta = NULL
        WHERE id = %s
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
    return df.values.tolist()

# =====================================================
# PERSONAL
# =====================================================

def obtener_personal():
    conn = get_connection()
    df = pd.read_sql("""
        SELECT id, nombre
        FROM personal
        ORDER BY nombre
    """, conn)
    cerrar(conn)
    return df


def obtener_personal_disponible(inicio, fin):
    conn = get_connection()
    df = pd.read_sql("""
        SELECT id, nombre
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
        ORDER BY nombre
    """, conn, params=(fin, inicio))
    cerrar(conn)
    return df
