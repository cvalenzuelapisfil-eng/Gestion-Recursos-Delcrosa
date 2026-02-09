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
# USUARIOS (AÑADIDO)
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
        SET password_hash = %s
        WHERE id = %s
    """, (hash_password(nueva_password), user_id))

    conn.commit()
    cerrar(conn, cur)


def cambiar_rol(user_id, nuevo_rol):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE usuarios
        SET rol = %s
        WHERE id = %s
    """, (nuevo_rol, user_id))

    conn.commit()
    cerrar(conn, cur)


def cambiar_estado(user_id, activo):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE usuarios
        SET activo = %s
        WHERE id = %s
    """, (activo, user_id))

    conn.commit()
    cerrar(conn, cur)


# =====================================================
# CRUD PROYECTOS (AÑADIDO)
# =====================================================

def crear_proyecto(nombre, inicio, fin, confirmado, usuario=None):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO proyectos (nombre, inicio, fin, confirmado, estado, eliminado)
        VALUES (%s, %s, %s, %s, 'Activo', FALSE)
        RETURNING id
    """, (nombre, inicio, fin, confirmado))

    proyecto_id = cur.fetchone()[0]
    conn.commit()
    cerrar(conn, cur)

    if usuario:
        registrar_auditoria(usuario, "CREAR", "PROYECTO", proyecto_id, nombre)


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
        registrar_auditoria(usuario, "ELIMINAR", "PROYECTO", pid, "")

# =====================================================
# ALERTAS POR PERSONA (AÑADIDO)
# =====================================================

def obtener_alertas_por_persona(personal_id=None):
    try:
        conn = get_connection()

        if personal_id:
            df = pd.read_sql("""
                SELECT pe.nombre, COUNT(*) AS total
                FROM asignaciones a1
                JOIN asignaciones a2
                  ON a1.personal_id = a2.personal_id
                 AND a1.id <> a2.id
                 AND a1.inicio <= a2.fin
                 AND a1.fin >= a2.inicio
                JOIN personal pe ON pe.id = a1.personal_id
                WHERE a1.activa = TRUE
                  AND a2.activa = TRUE
                  AND pe.id = %s
                GROUP BY pe.nombre
            """, conn, params=(personal_id,))
        else:
            df = pd.read_sql("""
                SELECT pe.nombre, COUNT(*) AS total
                FROM asignaciones a1
                JOIN asignaciones a2
                  ON a1.personal_id = a2.personal_id
                 AND a1.id <> a2.id
                 AND a1.inicio <= a2.fin
                 AND a1.fin >= a2.inicio
                JOIN personal pe ON pe.id = a1.personal_id
                WHERE a1.activa = TRUE
                  AND a2.activa = TRUE
                GROUP BY pe.nombre
            """, conn)

        cerrar(conn)

        alertas = []
        for _, r in df.iterrows():
            alertas.append(f"⚠️ {r['nombre']} tiene {int(r['total'])} solapamientos")

        return alertas

    except Exception:
        return []


# =====================================================
# GANTT DE PROYECTOS POR PERSONA (AÑADIDO)
# =====================================================

def proyectos_gantt_por_persona(personal_id=None):
    conn = get_connection()

    if personal_id:
        df = pd.read_sql("""
            SELECT 
                pr.nombre,
                pr.inicio,
                pr.fin,
                CASE WHEN pr.confirmado = TRUE 
                     THEN 'Confirmado'
                     ELSE 'No confirmado'
                END AS confirmacion
            FROM asignaciones a
            JOIN proyectos pr ON pr.id = a.proyecto_id
            WHERE a.activa = TRUE
              AND pr.eliminado = FALSE
              AND a.personal_id = %s
            ORDER BY pr.inicio
        """, conn, params=(personal_id,))
    else:
        df = pd.read_sql("""
            SELECT 
                pr.nombre,
                pr.inicio,
                pr.fin,
                CASE WHEN pr.confirmado = TRUE 
                     THEN 'Confirmado'
                     ELSE 'No confirmado'
                END AS confirmacion
            FROM proyectos pr
            WHERE pr.eliminado = FALSE
            ORDER BY pr.inicio
        """, conn)

    cerrar(conn)
    return df

# =====================================================
# TOTALES DASHBOARD
# =====================================================

def total_proyectos():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM proyectos WHERE eliminado = FALSE")
    total = cur.fetchone()[0]
    cerrar(conn, cur)
    return total


def total_personal():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM personal")
    total = cur.fetchone()[0]
    cerrar(conn, cur)
    return total


def total_asignaciones_activas():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM asignaciones WHERE activa = TRUE")
    total = cur.fetchone()[0]
    cerrar(conn, cur)
    return total


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
    return df   # ← NO lista

# =====================================================
# PERSONAL PARA DASHBOARD
# =====================================================

def obtener_personal_dashboard():
    conn = get_connection()
    df = pd.read_sql("""
        SELECT id, nombre
        FROM personal
        ORDER BY nombre
    """, conn)
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
        registrar_auditoria(usuario, "ASIGNAR", "ASIGNACION", proyecto_id, f"{len(personal_ids)} personas asignadas")


# =====================================================
# SUGERENCIA AUTOMÁTICA
# =====================================================

def sugerir_personal(inicio, fin, limite=5):
    conn = get_connection()

    df = pd.read_sql("""
        SELECT 
            p.id,
            p.nombre,
            COUNT(a.id) AS carga
        FROM personal p
        LEFT JOIN asignaciones a 
            ON a.personal_id = p.id
           AND a.activa = TRUE
           AND a.inicio <= %s
           AND a.fin >= %s
        GROUP BY p.id, p.nombre
        ORDER BY carga ASC, p.nombre
        LIMIT %s
    """, conn, params=(fin, inicio, limite))

    cerrar(conn)
    return df


# =====================================================
# CALENDARIO RECURSOS
# =====================================================

def calendario_recursos(inicio, fin):
    conn = get_connection()

    df = pd.read_sql("""
        SELECT 
            pe.nombre AS "Personal",
            pr.nombre AS "Proyecto",
            a.inicio AS "Inicio",
            a.fin AS "Fin"
        FROM asignaciones a
        JOIN personal pe ON pe.id = a.personal_id
        JOIN proyectos pr ON pr.id = a.proyecto_id
        WHERE a.activa = TRUE
          AND pr.eliminado = FALSE
          AND a.inicio <= %s
          AND a.fin >= %s
        ORDER BY pe.nombre, a.inicio
    """, conn, params=(fin, inicio))

    cerrar(conn)
    return df


# =====================================================
# KPIs
# =====================================================

def kpi_proyectos():
    conn = get_connection()
    df = pd.read_sql("SELECT estado FROM proyectos WHERE eliminado = FALSE", conn)
    cerrar(conn)

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

    cerrar(conn)
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
    cerrar(conn)
    return int(df.iloc[0]["total"])


def kpi_solapamientos():
    conn = get_connection()

    df = pd.read_sql("""
        SELECT COUNT(*) AS total
        FROM asignaciones a1
        JOIN asignaciones a2
          ON a1.personal_id = a2.personal_id
         AND a1.id <> a2.id
         AND a1.inicio <= a2.fin
         AND a1.fin >= a2.inicio
        WHERE a1.activa = TRUE
          AND a2.activa = TRUE
    """, conn)

    cerrar(conn)
    return int(df.iloc[0]["total"])


def kpi_proyectos_confirmados():
    conn = get_connection()

    df = pd.read_sql("""
        SELECT confirmado, COUNT(*) AS total
        FROM proyectos
        WHERE eliminado = FALSE
        GROUP BY confirmado
    """, conn)

    cerrar(conn)

    confirmados = int(df[df["confirmado"] == True]["total"].sum())
    no_confirmados = int(df[df["confirmado"] == False]["total"].sum())

    return confirmados, no_confirmados


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
