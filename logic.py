from database import get_connection

def agregar_personal(codigo, nombre, rol, disponible):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO personal (codigo, nombre, rol, disponible) VALUES (?,?,?,?)",
        (codigo, nombre, rol, int(disponible))
    )
    conn.commit()
    conn.close()

def listar_personal():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, codigo, nombre, rol, disponible FROM personal")
    rows = c.fetchall()
    conn.close()
    return rows
