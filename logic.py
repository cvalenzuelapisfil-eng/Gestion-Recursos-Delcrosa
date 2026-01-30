from database import conectar

def obtener_personal():
    conn = conectar()
    c = conn.cursor()
    c.execute("SELECT id, nombre, cargo, area, disponible FROM personal")
    data = c.fetchall()
    conn.close()
    return data

def marcar_no_disponible(personal_id):
    conn = conectar()
    c = conn.cursor()
    c.execute(
        "UPDATE personal SET disponible = 0 WHERE id = ?",
        (personal_id,)
    )
    conn.commit()
    conn.close()

def marcar_disponible(personal_id):
    conn = conectar()
    c = conn.cursor()
    c.execute(
        "UPDATE personal SET disponible = 1 WHERE id = ?",
        (personal_id,)
    )
    conn.commit()
    conn.close()
