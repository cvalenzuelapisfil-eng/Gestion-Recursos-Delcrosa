import sqlite3
import psycopg2

# ===============================
# CONEXIONES
# ===============================

SQLITE_DB = "data/gestion.db"

PG_CONN = psycopg2.connect(
    host="aws-1-us-east-1.pooler.supabase.com",
    dbname="postgres",
    user="postgres.folviontmigjpmjfmaxr",
    password="Traviesoss1",
    port=5432,
     sslmode="require"
)

sqlite_conn = sqlite3.connect(SQLITE_DB)
sqlite_conn.row_factory = sqlite3.Row

pg_cursor = PG_CONN.cursor()
sqlite_cursor = sqlite_conn.cursor()

# ===============================
# LIMPIAR TABLAS POSTGRES (OPCIONAL)
# ===============================
pg_cursor.execute("""
TRUNCATE TABLE
    asignaciones,
    proyectos_historial,
    personal_historial,
    proyectos,
    personal,
    usuarios
RESTART IDENTITY CASCADE
""")
PG_CONN.commit()

# ===============================
# MIGRAR PERSONAL
# ===============================
sqlite_cursor.execute("SELECT * FROM personal")
for row in sqlite_cursor.fetchall():
    pg_cursor.execute("""
        INSERT INTO personal (id, nombre, cargo, area)
        VALUES (%s, %s, %s, %s)
    """, (
        row["id"],
        row["nombre"],
        row["cargo"],
        row["area"]
    ))

# ===============================
# MIGRAR USUARIOS
# ===============================
sqlite_cursor.execute("SELECT * FROM usuarios")
for row in sqlite_cursor.fetchall():
    pg_cursor.execute("""
        INSERT INTO usuarios (id, usuario, password_hash, rol, activo)
        VALUES (%s, %s, %s, %s, %s)
    """, (
        row["id"],
        row["usuario"],
        row["password_hash"],
        row["rol"],
        bool(row["activo"])
    ))

# ===============================
# MIGRAR PROYECTOS
# ===============================
sqlite_cursor.execute("SELECT * FROM proyectos")
for row in sqlite_cursor.fetchall():
    pg_cursor.execute("""
        INSERT INTO proyectos (
            id, nombre, codigo, estado, inicio, fin, confirmado, eliminado
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        row["id"],
        row["nombre"],
        row["codigo"],
        row["estado"],
        row["inicio"],
        row["fin"],
        bool(row["confirmado"]),
        bool(row["eliminado"])
    ))

# ===============================
# MIGRAR ASIGNACIONES
# ===============================
sqlite_cursor.execute("SELECT * FROM asignaciones")
for row in sqlite_cursor.fetchall():
    pg_cursor.execute("""
        INSERT INTO asignaciones (
            id, personal_id, proyecto_id, inicio, fin, activa
        )
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        row["id"],
        row["personal_id"],
        row["proyecto_id"],
        row["inicio"],
        row["fin"],
        bool(row["activa"])
    ))

PG_CONN.commit()

# ===============================
# CERRAR
# ===============================
sqlite_conn.close()
pg_cursor.close()
PG_CONN.close()

print("✅ Migración completada correctamente")
