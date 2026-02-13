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
# PERSONAL
# =====================================================
def obtener_personal():
    conn = get_connection()
    df = pd.read_sql("""
        SELECT id,nombre,cargo,area,activo
        FROM personal
        ORDER BY nombre
    """, conn)
    cerrar(conn)
    return df


def obtener_personal_disponible(inicio, fin):
    conn = get_connection()

    df = pd.read_sql("""
        SELECT id,nombre
        FROM personal
        WHERE activo=TRUE
        AND id NOT IN (
            SELECT personal_id
            FROM asignaciones
            WHERE activa=TRUE
            AND inicio<=%s AND fin>=%s
        )
        ORDER BY nombre
    """, conn, params=(fin, inicio))

    cerrar(conn)
    return df


# =====================================================
# PROYECTOS
# =====================================================
def obtener_proyectos():
    conn = get_connection()
    df = pd.read_sql("""
        SELECT id,nombre,inicio,fin,confirmado,estado
        FROM proyectos
        WHERE eliminado=FALSE
        ORDER BY inicio DESC
    """, conn)
    cerrar(conn)
    return df


# =====================================================
# ASIGNACIONES
# =====================================================
def asignar_personal(proyecto_id, personal_ids, inicio, fin):
    conn = get_connection()
    cur = conn.cursor()

    for pid in personal_ids:
        cur.execute("""
            INSERT INTO asignaciones(personal_id,proyecto_id,inicio,fin,activa)
            VALUES(%s,%s,%s,%s,TRUE)
        """, (pid, proyecto_id, inicio, fin))

    conn.commit()
    cerrar(conn, cur)


def hay_solapamiento(pid, inicio, fin):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(*)
        FROM asignaciones
        WHERE personal_id=%s AND activa=TRUE
        AND inicio<=%s AND fin>=%s
    """, (pid, fin, inicio))

    res = cur.fetchone()[0] > 0
    cerrar(conn, cur)
    return res


def obtener_asignaciones_activas():
    conn = get_connection()
    df = pd.read_sql("""
        SELECT 
            p.nombre AS "Personal",
            pr.nombre AS "Proyecto",
            a.inicio AS "Inicio",
            a.fin AS "Fin"
        FROM asignaciones a
        JOIN personal p ON p.id = a.personal_id
        JOIN proyectos pr ON pr.id = a.proyecto_id
        WHERE a.activa = TRUE
        ORDER BY a.inicio
    """, conn)
    cerrar(conn)
    return df


# =====================================================
# CALENDARIO / DASHBOARD DATA
# =====================================================
def calendario_recursos(inicio=None, fin=None):
    conn = get_connection()

    df = pd.read_sql("""
        SELECT 
            p.nombre AS "Personal",
            pr.nombre AS "Proyecto",
            a.inicio AS "Inicio",
            a.fin AS "Fin"
        FROM asignaciones a
        JOIN personal p ON p.id = a.personal_id
        JOIN proyectos pr ON pr.id = a.proyecto_id
        WHERE a.activa = TRUE
        ORDER BY a.inicio
    """, conn)

    cerrar(conn)
    return df


def obtener_personal_dashboard():
    conn = get_connection()
    df = pd.read_sql("SELECT id, nombre FROM personal ORDER BY nombre", conn)
    cerrar(conn)
    return df


# =====================================================
# KPI DASHBOARD
# =====================================================
def kpi_proyectos():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM proyectos WHERE eliminado=FALSE")
    total = cur.fetchone()[0]
    cerrar(conn, cur)
    return total, 0


def kpi_personal():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM personal WHERE activo=TRUE")
    total = cur.fetchone()[0]
    cerrar(conn, cur)
    return total, 0, 0


def kpi_asignaciones():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM asignaciones WHERE activa=TRUE")
    total = cur.fetchone()[0]
    cerrar(conn, cur)
    return total


def kpi_solapamientos():
    return 0


def kpi_proyectos_confirmados():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) 
        FROM proyectos 
        WHERE confirmado=TRUE AND eliminado=FALSE
    """)
    total = cur.fetchone()[0]
    cerrar(conn, cur)
    return total, 0


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
