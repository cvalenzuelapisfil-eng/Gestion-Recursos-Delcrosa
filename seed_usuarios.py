import hashlib
from database import get_connection, crear_tablas

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def crear_usuario(usuario, password, rol):
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        INSERT OR REPLACE INTO usuarios (usuario, password_hash, rol, activo)
        VALUES (?, ?, ?, 1)
    """, (usuario, hash_password(password), rol))

    conn.commit()
    conn.close()

if __name__ == "__main__":
    crear_tablas()

    crear_usuario("admin", "admin123", "admin")
    crear_usuario("user", "user123", "usuario")

    print("✅ Usuarios creados correctamente")
