# ==============================

# LOGIC.PY — ERP ULTRA ESTABLE

# ==============================

import hashlib
import pandas as pd
from datetime import datetime, timedelta
from database import get_connection
import streamlit as st

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

# LOGIN SEGURO

# =====================================================

MAX_INTENTOS = 5
MINUTOS_BLOQUEO = 10

def validar_usuario(usuario, password):
conn = get_connection()
cur = conn.cursor()

```
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
```

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

# DISPONIBILIDAD

# =====================================================

def hay_solapamiento(personal_id, inicio, fin):
conn = get_connection()
cur = conn.cursor()

```
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
```

def obtener_personal():
conn = get_connection()
df = pd.read_sql("SELECT id, nombre FROM personal ORDER BY nombre", conn)
cerrar(conn)
return df

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

# =====================================================

# ERP ULTRA — CARGA

# =====================================================

def obtener_carga_personal(personal_id):
conn = get_connection()
cur = conn.cursor()

```
cur.execute("""
    SELECT COALESCE(COUNT(*), 0)
    FROM asignaciones
    WHERE personal_id = %s
      AND activa = TRUE
""", (personal_id,))

carga = cur.fetchone()[0]
cerrar(conn, cur)

return min(100, carga * 10)
```

# =====================================================

# ASIGNACIONES

# =====================================================

def asignar_personal(proyecto_id, personal_ids, inicio, fin, usuario=None):
conn = get_connection()
cur = conn.cursor()

```
for pid in personal_ids:
    cur.execute("""
        INSERT INTO asignaciones (personal_id, proyecto_id, inicio, fin, activa)
        VALUES (%s, %s, %s, %s, TRUE)
    """, (pid, proyecto_id, inicio, fin))

conn.commit()
cerrar(conn, cur)
```

# =====================================================

# CALENDARIO

# =====================================================

def calendario_recursos(inicio, fin):
conn = get_connection()

```
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
```

# =====================================================

# AUDITORIA

# =====================================================

def registrar_auditoria(usuario_id, accion, entidad, entidad_id=None, detalle=""):
try:
conn = get_connection()
cur = conn.cursor()

```
    cur.execute("""
        INSERT INTO auditoria (usuario_id, accion, entidad, entidad_id, detalle)
        VALUES (%s, %s, %s, %s, %s)
    """, (usuario_id, accion, entidad, entidad_id, detalle))

    conn.commit()
    cerrar(conn, cur)
except Exception:
    pass
```
