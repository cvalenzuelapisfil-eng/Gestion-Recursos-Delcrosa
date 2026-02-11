import hashlib
import secrets
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st
from database import get_connection


# =====================================================
# 🔐 SESIÓN SEGURA
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
# ROLES
# =====================================================
PERMISOS = {
    "admin": {
        "ver_dashboard", "gestionar_usuarios", "crear_proyecto",
        "editar_proyecto", "eliminar_proyecto", "asignar_personal",
        "editar_personal", "ver_auditoria"
    },
    "gestor": {
        "ver_dashboard", "crear_proyecto",
        "editar_proyecto", "asignar_personal", "editar_personal"
    },
    "usuario": {"ver_dashboard"}
}


def tiene_permiso(rol, permiso):
    return permiso in PERMISOS.get(rol, set())


# =====================================================
# PERSONAL
# =====================================================
def obtener_personal():
    conn = get_connection()
    df = pd.read_sql("SELECT id,nombre,cargo,area,activo FROM personal ORDER BY nombre", conn)
    cerrar(conn)
    return df


def obtener_personal_dashboard():
    conn = get_connection()
    df = pd.read_sql("SELECT id,nombre FROM personal ORDER BY nombre", conn)
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


def obtener_carga_personal(pid):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(*)
        FROM asignaciones
        WHERE personal_id=%s AND activa=TRUE
        AND fin>=CURRENT_DATE
    """, (pid,))

    total = cur.fetchone()[0]
    cerrar(conn, cur)

    return min(total * 20, 100)


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


def crear_proyecto(nombre, inicio, fin, confirmado, uid):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO proyectos(nombre,inicio,fin,confirmado,estado,eliminado)
        VALUES(%s,%s,%s,%s,'Activo',FALSE)
    """, (nombre, inicio, fin, confirmado))

    conn.commit()
    cerrar(conn, cur)


def modificar_proyecto(pid, nombre, inicio, fin, confirmado, uid):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE proyectos
        SET nombre=%s,inicio=%s,fin=%s,confirmado=%s
        WHERE id=%s
    """, (nombre, inicio, fin, confirmado, pid))

    conn.commit()
    cerrar(conn, cur)


def eliminar_proyecto(pid, uid):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE proyectos SET eliminado=TRUE WHERE id=%s", (pid,))
    conn.commit()
    cerrar(conn, cur)


# =====================================================
# ASIGNACIONES
# =====================================================
def asignar_personal(proyecto_id, personal_ids, inicio, fin, uid=None):
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
        SELECT p.nombre AS personal,
               pr.nombre AS proyecto,
               a.inicio,
               a.fin
        FROM asignaciones a
        JOIN personal p ON p.id=a.personal_id
        JOIN proyectos pr ON pr.id=a.proyecto_id
        WHERE a.activa=TRUE
    """, conn)
    cerrar(conn)
    return df


def calendario_recursos(*args, **kwargs):
    return obtener_asignaciones_activas()


def sugerir_personal(*args, **kwargs):
    return obtener_personal().head(5)


# =====================================================
# USUARIOS
# =====================================================
def obtener_usuarios():
    conn = get_connection()
    df = pd.read_sql("SELECT id,usuario,rol,activo,email FROM usuarios ORDER BY usuario", conn)
    cerrar(conn)
    return df


def crear_usuario(usuario, password, rol, creador_id=None):
    if st.session_state.rol != "admin":
        raise Exception("Solo admin puede crear usuarios")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO usuarios(usuario,password_hash,rol,activo)
        VALUES(%s,%s,%s,TRUE)
    """, (usuario, hash_password(password), rol))

    conn.commit()
    cerrar(conn, cur)


def cambiar_password(uid, pwd, solicitante_id=None):
    if st.session_state.user_id != uid and st.session_state.rol != "admin":
        raise Exception("No autorizado")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE usuarios
        SET password_hash=%s
        WHERE id=%s
    """, (hash_password(pwd), uid))

    conn.commit()
    cerrar(conn, cur)


def cambiar_rol(uid, rol):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE usuarios SET rol=%s WHERE id=%s", (rol, uid))
    conn.commit()
    cerrar(conn, cur)


def cambiar_estado(uid, activo):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE usuarios SET activo=%s WHERE id=%s", (activo, uid))
    conn.commit()
    cerrar(conn, cur)


# =====================================================
# RESET PASSWORD POR EMAIL (PREPARADO)
# =====================================================
def generar_token_reset(email):
    conn = get_connection()
    cur = conn.cursor()

    token = secrets.token_urlsafe(32)
    expira = datetime.now() + timedelta(minutes=30)

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
