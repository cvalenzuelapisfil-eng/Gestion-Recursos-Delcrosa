import streamlit as st
from logic import validar_usuario

st.set_page_config(
    page_title="Gestión de Recursos",
    layout="wide"
)

# ---------------------------
# SESSION STATE
# ---------------------------
if "usuario" not in st.session_state:
    st.session_state.usuario = None
    st.session_state.rol = None
    st.session_state.user_id = None

# ---------------------------
# LOGIN
# ---------------------------
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

# ---------------------------
# BLOQUEO TOTAL SIN LOGIN
# ---------------------------
if not st.session_state.usuario:
    login()
    st.stop()

# ---------------------------
# APP PRINCIPAL
# ---------------------------
st.sidebar.success(f"👤 {st.session_state.usuario}")
st.sidebar.info("Usa el menú lateral para navegar")

st.title("📌 Sistema de Gestión de Recursos")
st.write("Selecciona una opción en el menú lateral 👈")
