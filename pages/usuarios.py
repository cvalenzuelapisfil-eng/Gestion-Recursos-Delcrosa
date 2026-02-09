import streamlit as st
from logic import (
    tiene_permiso,
    obtener_usuarios,
    crear_usuario,
    cambiar_password,
    cambiar_rol,
    cambiar_estado,
    registrar_auditoria
)

st.set_page_config(page_title="Usuarios", layout="wide")

# =====================================================
# 🔐 SEGURIDAD POR ROL
# =====================================================
if not tiene_permiso(st.session_state.rol, "gestionar_usuarios"):
    st.error("⛔ No tienes permiso para acceder aquí")
    st.stop()

st.title("👥 Gestión de Usuarios")


# =====================================================
# CREAR USUARIO
# =====================================================
st.subheader("➕ Crear Usuario")

col1, col2, col3 = st.columns(3)

with col1:
    nuevo_usuario = st.text_input("Usuario")

with col2:
    nueva_password = st.text_input("Contraseña", type="password")

with col3:
    nuevo_rol = st.selectbox("Rol", ["usuario", "gestor", "admin"])

if st.button("Crear usuario"):

    if not nuevo_usuario or not nueva_password:
        st.warning("Completa todos los campos")
        st.stop()

    # Validar duplicado
    df = obtener_usuarios()
    if nuevo_usuario in df["usuario"].values:
        st.error("El usuario ya existe")
        st.stop()

    crear_usuario(nuevo_usuario, nueva_password, nuevo_rol)

    registrar_auditoria(
        st.session_state.user_id,
        "CREAR",
        "USUARIO",
        None,
        f"Usuario {nuevo_usuario} creado con rol {nuevo_rol}"
    )

    st.success("Usuario creado")
    st.rerun()


st.divider()


# =====================================================
# LISTA DE USUARIOS
# =====================================================
st.subheader("📋 Usuarios del sistema")

df = obtener_usuarios()

for _, row in df.iterrows():

    uid = int(row["id"])
    es_yo = uid == st.session_state.user_id

    col1, col2, col3, col4, col5 = st.columns([2,2,2,2,2])

    # -----------------------
    # USUARIO
    # -----------------------
    with col1:
        label = f"**{row['usuario']}**"
        if es_yo:
            label += " (Tú)"
        st.write(label)

    # -----------------------
    # CAMBIAR ROL
    # -----------------------
    with col2:

        nuevo_rol = st.selectbox(
            "Rol",
            ["usuario", "gestor", "admin"],
            index=["usuario","gestor","admin"].index(row["rol"]),
            key=f"rol_{uid}"
        )

        if nuevo_rol != row["rol"]:

            # No permitir quitarte admin a ti mismo
            if es_yo and row["rol"] == "admin" and nuevo_rol != "admin":
                st.error("⛔ No puedes quitarte el rol admin")
                st.stop()

            cambiar_rol(uid, nuevo_rol)

            registrar_auditoria(
                st.session_state.user_id,
                "EDITAR",
                "USUARIO",
                uid,
                f"Cambio de rol a {nuevo_rol}"
            )

            st.rerun()

    # -----------------------
    # ACTIVAR / DESACTIVAR
    # -----------------------
    with col3:

        estado = st.toggle(
            "Activo",
            value=bool(row["activo"]),
            key=f"activo_{uid}"
        )

        if estado != bool(row["activo"]):

            if es_yo and not estado:
                st.error("⛔ No puedes desactivarte a ti mismo")
                st.stop()

            cambiar_estado(uid, estado)

            registrar_auditoria(
                st.session_state.user_id,
                "EDITAR",
                "USUARIO",
                uid,
                f"Usuario {'activado' if estado else 'desactivado'}"
            )

            st.rerun()

    # -----------------------
    # RESET PASSWORD
    # -----------------------
    with col4:

        nueva_pass = st.text_input(
            "Nueva contraseña",
            type="password",
            key=f"pass_{uid}"
        )

        if st.button("Reset", key=f"reset_{uid}"):

            if not nueva_pass:
                st.warning("Introduce una contraseña")
                st.stop()

            cambiar_password(uid, nueva_pass)

            registrar_auditoria(
                st.session_state.user_id,
                "EDITAR",
                "USUARIO",
                uid,
                "Reset de contraseña"
            )

            st.success("Password actualizado")
            st.rerun()

    st.divider()
