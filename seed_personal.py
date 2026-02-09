import sqlite3
from pathlib import Path

DB_PATH = Path("data/gestion.db")
DB_PATH.parent.mkdir(exist_ok=True)

def get_connection():
    return sqlite3.connect(DB_PATH)

def crear_tablas():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS personal (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT,
        cargo TEXT,
        area TEXT,
        disponible INTEGER DEFAULT 1
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS proyectos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT,
        codigo TEXT,
        estado TEXT,
        inicio DATE,
        fin DATE,
        eliminado INTEGER DEFAULT 0
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS asignaciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        personal_id INTEGER,
        proyecto_id INTEGER,
        inicio DATE,
        fin DATE,
        activa INTEGER DEFAULT 1
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT UNIQUE,
        password_hash TEXT,
        rol TEXT,
        activo INTEGER DEFAULT 1
    )
    """)

    conn.commit()
    conn.close()
