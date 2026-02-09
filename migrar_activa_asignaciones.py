import sqlite3
from pathlib import Path

DB_PATH = Path("data/gestion.db")

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

try:
    c.execute("ALTER TABLE asignaciones ADD COLUMN activa INTEGER DEFAULT 1")
    print("✅ Columna 'activa' agregada correctamente")
except sqlite3.OperationalError as e:
    print("ℹ️ La columna ya existe:", e)

conn.commit()
conn.close()
