import sqlite3

def get_connection():
    return sqlite3.connect("gestion_recursos.db", check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS personal (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT,
        nombre TEXT,
        rol TEXT,
        disponible INTEGER
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS asignaciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo_proyecto TEXT,
        personal_id INTEGER,
        fecha_inicio TEXT,
        fecha_fin TEXT
    )
    """)

    conn.commit()
    conn.close()

