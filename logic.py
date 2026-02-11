import hashlib
import secrets
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st
from database import get_connection


# =====================================================
# SESIÓN
# =====================================================
def asegurar_sesion():
    st.session_state.setdefault("autenticado", False)
    st.session_state.setdefault("usuario", None)
    st.session_state.setdefault("rol", "publico")
    st.session_state.setdefault("user_id", None)


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

    if not activo or hash_password(password) != pwd:
        cerrar(conn, cur)
        return None

    cerrar(conn, cur)
    return uid, user, rol


# =====================================================
# PERMISOS
# =====================================================
PERMISOS = {
    "admin": {"ver_dashboard","gestionar_usuarios","crear_proyecto",
              "editar_proyecto","eliminar_proyecto","asignar_personal",
              "editar_personal","ver_auditoria"},
    "gestor": {"ver_dashboard","crear_proyecto","editar_proyecto",
               "asignar_personal","editar_personal"},
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


# 🔐 SOLO ADMIN CREA
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


# 🔐 CADA USUARIO CAMBIA SU PASSWORD
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
# RESET PASSWORD (EMAIL PREPARADO)
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
