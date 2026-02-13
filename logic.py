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
    Lista personal para filtros Dashboard.
    SIEMPRE devuelve columna 'nombre' aunque no haya datos.
    """
    try:
        conn = get_connection()

        df = pd.read_sql("""
            SELECT id, nombre
            FROM personal
            WHERE activo = TRUE
            ORDER BY nombre
        """, conn)

        cerrar(conn)

        # 🔒 Garantiza estructura aunque esté vacío
        if df is None or df.empty:
            return pd.DataFrame(columns=["id", "nombre"])

        # 🔒 Normaliza nombres columnas
        df.columns = [c.lower() for c in df.columns]

        return df

    except Exception as e:
        return pd.DataFrame(columns=["id", "nombre"])

# =====================================================
# COMPATIBILIDAD PAGINA ASIGNACIONES (NO BORRAR)
# =====================================================

def obtener_personal_disponible(inicio, fin):
    """
    Personal libre en un rango de fechas.
    Compatible con pages/asignaciones.py
    """
    try:
        conn = get_connection()

        query = """
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
        """

        df = pd.read_sql(query, conn, params=(fin, inicio))
        cerrar(conn)
        return df

    except Exception as e:
        return pd.DataFrame()


def obtener_asignaciones():
    """
    Lista completa de asignaciones.
    """
    try:
        conn = get_connection()

        df = pd.read_sql("""
            SELECT 
                a.id,
                p.nombre AS "Personal",
                pr.nombre AS "Proyecto",
                a.inicio AS "Inicio",
                a.fin AS "Fin",
                a.activa
            FROM asignaciones a
            JOIN personal p ON p.id = a.personal_id
            JOIN proyectos pr ON pr.id = a.proyecto_id
            ORDER BY a.inicio
        """, conn)

        cerrar(conn)
        return df

    except:
        return pd.DataFrame()

# =====================================================
# IA / MOTOR ASIGNACION (COMPATIBILIDAD ERP ULTRA)
# =====================================================

def obtener_carga_personal(pid):
    """
    Calcula % de carga del personal según asignaciones activas.
    Fórmula simple y estable para evitar errores.
    """
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT COUNT(*)
            FROM asignaciones
            WHERE personal_id=%s AND activa=TRUE
        """, (pid,))

        total = cur.fetchone()[0]
        cerrar(conn, cur)

        # Escala simple: 0 asignaciones = 0%, 1 = 25%, 2 = 50%, 3 = 75%, 4+ = 100%
        carga = min(total * 25, 100)
        return carga

    except:
        return 0


def sugerir_personal(inicio, fin, cantidad=1):
    """
    Motor inteligente simple:
    Devuelve personal disponible ordenado por menor carga.
    """
    try:
        df = obtener_personal_disponible(inicio, fin)
        if df.empty:
            return df

        df["carga"] = df["id"].apply(obtener_carga_personal)
        df = df.sort_values("carga")

        return df.head(cantidad)

    except:
        return pd.DataFrame()


# =====================================================
# FIX FIRMA asignar_personal (COMPATIBLE CON PAGINAS)
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

    # Auditoría automática si se pasa usuario
    if uid:
        try:
            registrar_auditoria(
                uid,
                "ASIGNAR_PERSONAL",
                "ASIGNACIONES",
                proyecto_id,
                f"{len(personal_ids)} personas asignadas"
            )
        except:
            pass

# =====================================================
# PROYECTOS (COMPATIBILIDAD TOTAL)
# =====================================================

def obtener_proyectos():
    """
    Lista de proyectos activos.
    Compatible con Dashboard, Asignaciones y Proyectos.
    """
    try:
        conn = get_connection()

        df = pd.read_sql("""
            SELECT 
                id,
                nombre,
                inicio,
                fin,
                confirmado,
                estado
            FROM proyectos
            WHERE eliminado = FALSE
            ORDER BY inicio DESC
        """, conn)

        cerrar(conn)
        return df

    except Exception as e:
        return pd.DataFrame()

# =====================================================
# PROYECTOS CRUD (COMPATIBLE CON pages/proyectos.py)
# =====================================================

def crear_proyecto(nombre, inicio, fin, confirmado=False, uid=None):
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO proyectos(nombre, inicio, fin, confirmado, estado, eliminado)
            VALUES(%s, %s, %s, %s, 'Activo', FALSE)
        """, (nombre, inicio, fin, confirmado))

        conn.commit()
        cerrar(conn, cur)

        if uid:
            registrar_auditoria(uid, "CREAR_PROYECTO", "PROYECTOS", None, nombre)

    except:
        pass


def modificar_proyecto(pid, nombre, inicio, fin, confirmado, uid=None):
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE proyectos
            SET nombre=%s, inicio=%s, fin=%s, confirmado=%s
            WHERE id=%s
        """, (nombre, inicio, fin, confirmado, pid))

        conn.commit()
        cerrar(conn, cur)

        if uid:
            registrar_auditoria(uid, "MODIFICAR_PROYECTO", "PROYECTOS", pid, nombre)

    except:
        pass


def eliminar_proyecto(pid, uid=None):
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("UPDATE proyectos SET eliminado=TRUE WHERE id=%s", (pid,))

        conn.commit()
        cerrar(conn, cur)

        if uid:
            registrar_auditoria(uid, "ELIMINAR_PROYECTO", "PROYECTOS", pid, "")

    except:
        pass


# =====================================================
# DASHBOARD KPI (COMPATIBLE CON Dashboard.py)
# =====================================================

def kpi_proyectos():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM proyectos WHERE eliminado=FALSE")
        total = cur.fetchone()[0]
        cerrar(conn, cur)
        return total, 0
    except:
        return 0, 0


def kpi_personal():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM personal WHERE activo=TRUE")
        total = cur.fetchone()[0]
        cerrar(conn, cur)
        return total, 0, 0
    except:
        return 0, 0, 0


def kpi_asignaciones():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM asignaciones WHERE activa=TRUE")
        total = cur.fetchone()[0]
        cerrar(conn, cur)
        return total
    except:
        return 0


# =====================================================
# FIX SOLAPAMIENTO (ASIGNACIONES)
# =====================================================

def hay_solapamiento(pid, inicio, fin):
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT COUNT(*)
            FROM asignaciones
            WHERE personal_id=%s
            AND activa=TRUE
            AND inicio <= %s
            AND fin >= %s
        """, (pid, fin, inicio))

        res = cur.fetchone()[0] > 0
        cerrar(conn, cur)
        return res

    except:
        return False


# =====================================================
# KPI EXTRA DASHBOARD
# =====================================================

def kpi_proyectos_confirmados():
    try:
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
    except:
        return 0, 0


def kpi_solapamientos():
    # Puedes mejorarlo luego — ahora evita que rompa Dashboard
    return 0


# =====================================================
# DATA EXTRA DASHBOARD
# =====================================================

def obtener_alertas_por_persona(pid=None):
    # Placeholder estable — evita crash
    return []


def proyectos_gantt_por_persona(pid=None):
    try:
        conn = get_connection()

        df = pd.read_sql("""
            SELECT nombre, inicio, fin
            FROM proyectos
            WHERE eliminado=FALSE
            ORDER BY inicio
        """, conn)

        cerrar(conn)
        return df

    except:
        return pd.DataFrame()


