import hashlib
from datetime import date
import pandas as pd
from database import get_connection


# ==============================
# UTILIDADES
# ==============================

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


# ==============================
# LOGIN
# ==============================

def validar_usuario(usuario, password):
    conn = get_connection()
    cur = conn.cursor()

    # HASH SHA256 IGUAL AL DE SUPABASE
    password_hash = hashlib.sha256(password.encode()).hexdigest()

    cur.execute("""
        SELECT id, usuario, rol
        FROM usuarios
        WHERE usuario = %s
        AND password_hash = %s
        AND activo = true
    """, (usuario, password_hash))

    user = cur.fetchone()
    cur.close()
    conn.close()
    return user
# =====================================================
# CALENDARIO RECURSOS
# =====================================================

import pandas as pd
from database import get_connection


def calendario_recursos(fecha_inicio, fecha_fin):
    conn = get_connection()

    query = """
        SELECT 
            pr.nombre AS "Proyecto",
            pe.nombre AS "Personal",
            a.inicio AS "Inicio",
            a.fin AS "Fin"
        FROM asignaciones a
        JOIN proyectos pr ON a.proyecto_id = pr.id
        JOIN personal pe ON a.personal_id = pe.id
        WHERE a.fin >= %s
          AND a.inicio <= %s
          AND a.activa = TRUE
        ORDER BY a.inicio
    """

    df = pd.read_sql(query, conn, params=(fecha_inicio, fecha_fin))
    conn.close()
    return df



# ==============================
# PROYECTOS
# ==============================

def obtener_proyectos():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        SELECT id, nombre, codigo, estado, inicio, fin, confirmado
        FROM proyectos
        WHERE eliminado = FALSE
        ORDER BY inicio DESC
    """)

    filas = c.fetchall()
    conn.close()
    return filas


def crear_proyecto(nombre, inicio, fin, confirmado, usuario):
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        INSERT INTO proyectos (nombre, codigo, estado, inicio, fin, confirmado, eliminado)
        VALUES (%s, '', 'Activo', %s, %s, %s, FALSE)
        RETURNING id
    """, (nombre, inicio, fin, bool(confirmado)))

    proyecto_id = c.fetchone()[0]
    codigo = f"{nombre[:6].upper()}-{proyecto_id}"

    c.execute("""
        UPDATE proyectos SET codigo = %s WHERE id = %s
    """, (codigo, proyecto_id))

    conn.commit()
    conn.close()


def eliminar_proyecto(proyecto_id):
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        UPDATE proyectos SET eliminado = TRUE WHERE id = %s
    """, (proyecto_id,))

    c.execute("""
        UPDATE asignaciones SET activa = FALSE WHERE proyecto_id = %s
    """, (proyecto_id,))

    conn.commit()
    conn.close()
# ==============================
# PERSONAL DISPONIBLE
# ==============================

def obtener_personal_disponible(inicio, fin):
    """
    Devuelve personal que NO tiene asignaciones solapadas
    en el rango de fechas indicado.
    """
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
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
    """, (fin, inicio))

    filas = c.fetchall()
    conn.close()
    return filas

# ==============================
# PLACEHOLDERS PARA DASHBOARD
# ==============================

def obtener_asignaciones():
    conn = get_connection()
    df = pd.read_sql("""
        SELECT 
            a.id,
            pr.nombre AS proyecto,
            pe.nombre AS personal,
            a.inicio,
            a.fin,
            a.activa
        FROM asignaciones a
        JOIN proyectos pr ON pr.id = a.proyecto_id
        JOIN personal pe ON pe.id = a.personal_id
        WHERE pr.eliminado = FALSE
    """, conn)
    conn.close()
    return df


def proyectos_activos():
    conn = get_connection()
    df = pd.read_sql("""
        SELECT *
        FROM proyectos
        WHERE eliminado = FALSE
          AND estado = 'Activo'
    """, conn)
    conn.close()
    return df


def personal_ocupado():
    conn = get_connection()
    df = pd.read_sql("""
        SELECT DISTINCT pe.nombre
        FROM asignaciones a
        JOIN personal pe ON pe.id = a.personal_id
        JOIN proyectos pr ON pr.id = a.proyecto_id
        WHERE a.activa = TRUE
          AND pr.eliminado = FALSE
    """, conn)
    conn.close()
    return df


def kpi_resumen():
    activos, cerrados = kpi_proyectos()
    total, libres, ocupados = kpi_personal()
    asignaciones = kpi_asignaciones()

    return {
        "proyectos_activos": activos,
        "proyectos_cerrados": cerrados,
        "personal_total": total,
        "personal_libre": libres,
        "personal_ocupado": ocupados,
        "asignaciones": asignaciones
    }


def resumen_persona(nombre_persona):
    conn = get_connection()
    df = pd.read_sql("""
        SELECT 
            pr.nombre AS proyecto,
            a.inicio,
            a.fin
        FROM asignaciones a
        JOIN personal pe ON pe.id = a.personal_id
        JOIN proyectos pr ON pr.id = a.proyecto_id
        WHERE pe.nombre = %s
          AND a.activa = TRUE
          AND pr.eliminado = FALSE
        ORDER BY a.inicio
    """, conn, params=(nombre_persona,))
    conn.close()
    return df


# ==============================
# PERSONAL
# ==============================

def obtener_personal():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        SELECT id, nombre
        FROM personal
        ORDER BY nombre
    """)

    filas = c.fetchall()
    conn.close()
    return filas


def hay_solapamiento(personal_id, inicio, fin):
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        SELECT COUNT(*)
        FROM asignaciones a
        JOIN proyectos p ON p.id = a.proyecto_id
        WHERE a.personal_id = %s
          AND p.eliminado = FALSE
          AND a.activa = TRUE
          AND a.inicio <= %s
          AND a.fin >= %s
    """, (personal_id, fin, inicio))

    existe = c.fetchone()[0] > 0
    conn.close()
    return existe


def asignar_personal(proyecto_id, personal_ids, inicio, fin):
    conn = get_connection()
    c = conn.cursor()

    for pid in personal_ids:
        c.execute("""
            INSERT INTO asignaciones (personal_id, proyecto_id, inicio, fin, activa)
            VALUES (%s, %s, %s, %s, TRUE)
        """, (pid, proyecto_id, inicio, fin))

    conn.commit()
    conn.close()


# ==============================
# KPIs
# ==============================

def kpi_proyectos():
    conn = get_connection()
    df = pd.read_sql("SELECT estado FROM proyectos WHERE eliminado = FALSE", conn)
    conn.close()

    activos = len(df[df["estado"] == "Activo"])
    cerrados = len(df[df["estado"] != "Activo"])
    return activos, cerrados


def kpi_personal():
    conn = get_connection()

    total = pd.read_sql("SELECT COUNT(*) AS t FROM personal", conn)["t"][0]

    ocupados = pd.read_sql("""
        SELECT COUNT(DISTINCT a.personal_id) AS o
        FROM asignaciones a
        JOIN proyectos p ON p.id = a.proyecto_id
        WHERE a.activa = TRUE
          AND p.eliminado = FALSE
    """, conn)["o"][0]

    conn.close()
    return total, total - ocupados, ocupados

def kpi_asignaciones():
    conn = get_connection()
    df = pd.read_sql("""
        SELECT COUNT(*) AS total
        FROM asignaciones a
        JOIN proyectos p ON p.id = a.proyecto_id
        WHERE a.activa = TRUE
          AND p.eliminado = FALSE
    """, conn)
    conn.close()
    return int(df.iloc[0]["total"])
