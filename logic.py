import hashlib
import secrets
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st
from database import get_connection

# =====================================================
# SESIÓN GLOBAL
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
# UTIL
# =====================================================
def cerrar(conn, cur=None):
    try:
        if cur:
            cur.close()
    finally:
        conn.close()


def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()


# =====================================================
# LOGIN
# =====================================================
def validar_usuario(usuario, password):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, usuario, rol, password_hash, activo
        FROM usuarios
        WHERE usuario=%s
    """, (usuario,))
    row = cur.fetchone()

    if not row:
        cerrar(conn, cur)
        return None

    uid, user, rol, pwd, activo = row

    if not activo:
        cerrar(conn, cur)
        return None

    if hash_password(password) != pwd:
        cerrar(conn, cur)
        return None

    cerrar(conn, cur)
    return uid, user, rol


# =====================================================
# PERMISOS
# =====================================================
PERMISOS = {
    "admin": {
        "ver_dashboard","gestionar_usuarios","crear_proyecto",
        "editar_proyecto","eliminar_proyecto","asignar_personal",
        "editar_personal","ver_auditoria"
    },
    "gestor": {
        "ver_dashboard","crear_proyecto","editar_proyecto",
        "asignar_personal","editar_personal"
    },
    "usuario": {"ver_dashboard"}
}

def tiene_permiso(rol, permiso):
    return permiso in PERMISOS.get(rol, set())


# =====================================================
# USUARIOS
# =====================================================
def obtener_usuarios():
    conn = get_connection()
    df = pd.read_sql("""
        SELECT id, usuario, rol, activo, email
        FROM usuarios
        ORDER BY usuario
    """, conn)
    cerrar(conn)
    return df


def crear_usuario(usuario, password, rol, email=None):
    if st.session_state.rol != "admin":
        raise Exception("Solo admin puede crear usuarios")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO usuarios(usuario,password_hash,rol,activo,email)
        VALUES(%s,%s,%s,TRUE,%s)
    """, (usuario, hash_password(password), rol, email))

    conn.commit()
    cerrar(conn, cur)


def cambiar_password(uid, nueva_password):
    if st.session_state.user_id != uid and st.session_state.rol != "admin":
        raise Exception("No autorizado")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE usuarios
        SET password_hash=%s
        WHERE id=%s
    """, (hash_password(nueva_password), uid))

    conn.commit()
    cerrar(conn, cur)


def cambiar_rol(uid, rol):
    if st.session_state.rol != "admin":
        raise Exception("Solo admin")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("UPDATE usuarios SET rol=%s WHERE id=%s", (rol, uid))

    conn.commit()
    cerrar(conn, cur)


def cambiar_estado(uid, activo):
    if st.session_state.rol != "admin":
        raise Exception("Solo admin")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("UPDATE usuarios SET activo=%s WHERE id=%s", (activo, uid))

    conn.commit()
    cerrar(conn, cur)


# =====================================================
# RESET PASSWORD
# =====================================================
def generar_token_reset(email):
    token = secrets.token_urlsafe(32)
    expira = datetime.now() + timedelta(minutes=30)

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE usuarios
        SET reset_token=%s, reset_expira=%s
        WHERE email=%s
    """, (token, expira, email))

    conn.commit()
    cerrar(conn, cur)

    return token


def reset_password_por_token(token, nueva_password):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id FROM usuarios
        WHERE reset_token=%s AND reset_expira > NOW()
    """, (token,))
    row = cur.fetchone()

    if not row:
        cerrar(conn, cur)
        return False

    uid = row[0]

    cur.execute("""
        UPDATE usuarios
        SET password_hash=%s,
            reset_token=NULL,
            reset_expira=NULL
        WHERE id=%s
    """, (hash_password(nueva_password), uid))

    conn.commit()
    cerrar(conn, cur)
    return True


# =====================================================
# AUDITORIA
# =====================================================
def registrar_auditoria(uid, accion, modulo, ref, detalle):
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO auditoria(usuario_id,accion,modulo,referencia,detalle,fecha)
            VALUES(%s,%s,%s,%s,%s,NOW())
        """, (uid, accion, modulo, ref, detalle))

        conn.commit()
        cerrar(conn, cur)

    except:
        pass
# =====================================================
# COMPATIBILIDAD CALENDARIO (NO BORRAR)
# =====================================================

def calendario_recursos(inicio=None, fin=None):
    """
    Devuelve asignaciones activas para calendario.
    Compatible con pages/calendario_recursos.py
    """
    try:
        conn = get_connection()

        query = """
            SELECT 
                a.id,
                p.nombre AS "Personal",
                pr.nombre AS "Proyecto",
                a.inicio AS "Inicio",
                a.fin AS "Fin"
            FROM asignaciones a
            JOIN personal p ON p.id = a.personal_id
            JOIN proyectos pr ON pr.id = a.proyecto_id
            WHERE a.activa = TRUE
            ORDER BY a.inicio
        """

        df = pd.read_sql(query, conn)
        cerrar(conn)
        return df

    except Exception as e:
        return pd.DataFrame()


def obtener_personal_dashboard():
    """
    Lista simple para filtros del calendario/dashboard.
    """
    try:
        conn = get_connection()
        df = pd.read_sql(
            "SELECT id, nombre FROM personal WHERE activo=TRUE ORDER BY nombre",
            conn
        )
        cerrar(conn)
        return df
    except:
        return pd.DataFrame()

    
