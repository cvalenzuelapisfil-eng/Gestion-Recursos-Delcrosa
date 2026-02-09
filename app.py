import streamlit as st
from logic import validar_usuario
from logic import tiene_permiso


st.set_page_config(
    page_title="Gestión de Recursos",
    layout="wide"
)

# =====================================================
# SESSION STATE
# =====================================================
if "usuario" not in st.session_state:
    st.session_state.usuario = None
    st.session_state.rol = None
    st.session_state.user_id = None


# =====================================================
# LOGIN
# =====================================================
def login():
    st.title("🔐 Iniciar sesión")

    usuario = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")

    if st.button("Ingresar"):
        try:
            user = validar_usuario(usuario, password)

            if user:
                st.session_state.user_id = user[0]
                st.session_state.usuario = user[1]
                st.session_state.rol = user[2]
                st.rerun()
            else:
                st.error("Credenciales inválidas")

        except Exception as e:
            st.error("Error conectando con la base de datos")
            st.exception(e)


# =====================================================
# LOGOUT
# =====================================================
def logout():
    st.session_state.usuario = None
    st.session_state.rol = None
    st.session_state.user_id = None
    st.rerun()

# =====================================================
# GUARDIÁN DE PERMISOS
# =====================================================
def permiso_requerido(permiso):
    if not tiene_permiso(st.session_state.rol, permiso):
        st.error("⛔ No tienes permiso para acceder a esta sección")
        st.stop()

# =====================================================
# BLOQUEO TOTAL SIN LOGIN
# =====================================================
if not st.session_state.usuario:
    login()
    st.stop()


# =====================================================
# SIDEBAR
# =====================================================
st.sidebar.success(f"👤 {st.session_state.usuario}")
st.sidebar.caption(f"Rol: {st.session_state.rol}")

if st.sidebar.button("🚪 Cerrar sesión"):
    logout()

st.sidebar.divider()
st.sidebar.title("📂 Menú")

rol = st.session_state.rol

# Dashboard (todos)
st.sidebar.page_link("app.py", label="Dashboard")

# Proyectos / Asignaciones (admin + gestor)
if rol in ["admin", "gestor"]:
    st.sidebar.page_link("pages/proyectos.py", label="Proyectos")
    st.sidebar.page_link("pages/asignaciones.py", label="Asignaciones")

# Calendario (todos)
st.sidebar.page_link("calendario.py", label="Calendario")

# Usuarios (solo admin)
if rol == "admin":
    st.sidebar.page_link("pages/usuarios.py", label="Usuarios")


# =====================================================
# PANTALLA PRINCIPAL
# =====================================================
st.title("📌 Sistema de Gestión de Recursos")
st.write("Selecciona una opción en el menú lateral 👈")
