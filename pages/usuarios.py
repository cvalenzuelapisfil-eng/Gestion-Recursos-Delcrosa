import streamlit as st
from logic import (
    asegurar_sesion,
    tiene_permiso,
    obtener_usuarios,
    crear_usuario,
    cambiar_password,
    cambiar_rol,
    cambiar_estado,
    registrar_auditoria
)

# =====================================================
# CONFIG
# =====================================================
st.set_page_config(page_title="Usuarios", layout="wide")

# =====================================================
# 🔐 SEGURIDAD GLOBAL
# =====================================================
asegurar_sesion()

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

    if not nuevo_usuario.strip() or not nueva_password.strip():
        st.warning("Completa todos los campos")
    else:
        df = obtener_usuarios()

        if nuevo_usuario in df["usuario"].values:
            st.error("El usuario ya existe")
        else:
            crear_usuario(nuevo_usuario, nueva_password, nuevo_rol)

            registrar_auditoria(
                st.session_state.usuario_id,
                "CREAR",
                "USUARIO",
                None,
                f"Usuario {nuevo_usuario} creado con rol {nuevo_rol}"
            )

            st.success("Usuario creado correctamente")
            st.rerun()

st.divider()

# =====================================================
# LISTA DE USUARIOS
# =====================================================
st.subheader("📋 Usuarios del sistema")

df = obtener_usuarios()

if df.empty:
    st.info("No hay usuarios registrados")
    st.stop()

for _, row in df.iterrows():

    uid = int(row["id"])
    es_yo = uid == st.session_state.usuario_id

    col1, col2, col3, col4 = st.columns([3, 3, 3, 3])

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

        rol_sel = st.selectbox(
            "Rol",
            ["usuario", "gestor", "admin"],
            index=["usuario", "gestor", "admin"].index(row["rol"]),
            key=f"rol_{uid}"
        )

        if rol_sel != row["rol"]:

            if es_yo and row["rol"] == "admin" and rol_sel != "admin":
                st.error("⛔ No puedes quitarte el rol admin")
            else:
                cambiar_rol(uid, rol_sel)

                registrar_auditoria(
                    st.session_state.usuario_id,
                    "EDITAR",
                    "USUARIO",
                    uid,
                    f"Cambio de rol a {rol_sel}"
                )

                st.success("Rol actualizado")
                st.rerun()

    # -----------------------
    # ACTIVAR / DESACTIVAR
    # -----------------------
    with col3:

        activo = st.toggle(
            "Activo",
            value=bool(row["activo"]),
            key=f"activo_{uid}"
        )

        if activo != bool(row["activo"]):

            if es_yo and not activo:
                st.error("⛔ No puedes desactivarte a ti mismo")
            else:
                cambiar_estado(uid, activo)

                registrar_auditoria(
                    st.session_state.usuario_id,
                    "EDITAR",
                    "USUARIO",
                    uid,
                    f"Usuario {'activado' if activo else 'desactivado'}"
                )

                st.success("Estado actualizado")
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

            if not nueva_pass.strip():
                st.warning("Introduce una contraseña")
            else:
                cambiar_password(uid, nueva_pass)

                registrar_auditoria(
                    st.session_state.usuario_id,
                    "EDITAR",
                    "USUARIO",
                    uid,
                    "Reset de contraseña"
                )

                st.success("Contraseña actualizada")
                st.rerun()

    st.divider()
