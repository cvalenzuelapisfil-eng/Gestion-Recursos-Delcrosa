import sqlite3
import os

DB_PATH = "data/recursos.db"

PERSONAL_INICIAL = [
    ("Cinthya Bellido", "Administradora", "Oficina"),
    ("Antonio Velasco", "Jefe de Servicios", "Servicios"),
    ("Christian Valenzuela", "Coord. Servicios", "Servicios"),
    ("Marco Subelete", "Coord. Servicios", "Servicios"),
    ("Juan Espinoza", "Ing. Comunicación", "Ingeniería"),
    ("Juan Pilco", "Ing. Sup. Servicios", "Ingeniería"),
    ("Wilber Chiclla", "Ing. Sup. Servicios", "Ingeniería"),
    ("Luis Flores", "Sup. Seguridad", "Seguridad"),
    ("Victor Salazar", "Sup. Seguridad", "Seguridad"),
    ("Lilian Huaman", "Sup. Seguridad", "Seguridad"),
    ("Everly Tapia", "Conductor", "Movilidad"),
    ("Segundo Gícaro", "Camión Grúa", "Obras"),
    ("Wiler Coppa", "Coord. Servicios", "Arequipa"),
    ("Kelly Luna", "Sup. Seguridad", "Arequipa"),
]

def conectar():
    os.makedirs("data", exist_ok=True)
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def crear_tablas_y_seed():
    conn = conectar()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS personal (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        cargo TEXT NOT NULL,
        area TEXT,
        disponible INTEGER DEFAULT 1
    )
    """)

    # 🔹 Verificar si ya hay datos
    c.execute("SELECT COUNT(*) FROM personal")
    cantidad = c.fetchone()[0]

    if cantidad == 0:
        c.executemany(
            "INSERT INTO personal (nombre, cargo, area, disponible) VALUES (?, ?, ?, 1)",
            PERSONAL_INICIAL
        )

    conn.commit()
    conn.close()
