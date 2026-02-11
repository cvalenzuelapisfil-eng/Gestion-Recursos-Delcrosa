# ==============================

# LOGIC.PY — ERP ULTRA UNIFICADO

# ==============================

import hashlib
import pandas as pd
from datetime import datetime, timedelta
from database import get_connection
import streamlit as st

# =====================================================

# SESIÓN GLOBAL STREAMLIT

# =====================================================

def asegurar_sesion():
if "autenticado" not in st.session_state:
st.session_state.autenticado = False

```
if "usuario" not in st.session_state:
    st.session_state.usuario = None

if "rol" not in st.session_state:
    st.session_state.rol = "publico"

if "user_id" not in st.session_state:
    st.session_state.user_id = None
```

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

# DISPONIBILIDAD Y SOLAPAMIENTOS

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

def obtener_personal_disponible(inicio, fin):
conn = get_connection()

```
df = pd.read_sql("""
    SELECT p.id, p.nombre
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
    ORDER BY p.nombre
""", conn, params=(fin, inicio))

cerrar(conn)
return df
```

def sugerir_personal(inicio, fin):
conn = get_connection()

```
df = pd.read_sql("""
    SELECT p.id, p.nombre, COUNT(a.id) AS carga
    FROM personal p
    LEFT JOIN asignaciones a
        ON a.personal_id = p.id
       AND a.activa = TRUE
       AND a.inicio <= %s
       AND a.fin >= %s
    GROUP BY p.id, p.nombre
    ORDER BY carga ASC, p.nombre
    LIMIT 5
""", conn, params=(fin, inicio))

cerrar(conn)
return df
```

# =====================================================

# ERP ULTRA — CARGA INTELIGENTE

# =====================================================

def obtener_carga_personal(personal_id):
conn = get_connection()
cur = conn.cursor()

```
cur.execute("""
    SELECT COALESCE(SUM(
        GREATEST(0, LEAST(fin, CURRENT_DATE + INTERVAL '30 days') - inicio)
    ), 0)
    FROM asignaciones
    WHERE personal_id = %s
      AND activa = TRUE
      AND fin >= CURRENT_DATE
""", (personal_id,))

dias = cur.fetchone()[0] or 0
cerrar(conn, cur)

carga = int((dias / 30) * 100)

if carga > 100:
    carga = 100
if carga < 0:
    carga = 0

return carga
```

# =====================================================

# PERSONAL

# =====================================================

def obtener_personal():
conn = get_connection()
df = pd.read_sql("SELECT id, nombre FROM personal ORDER BY nombre", conn)
cerrar(conn)
return df

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
return df

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

# CALENDARIO (FIX KeyError)

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
