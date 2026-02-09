import streamlit as st

def requiere_login():
    if "usuario" not in st.session_state:
        st.warning("Debes iniciar sesión")
        st.stop()

def requiere_rol(*roles):
    requiere_login()
    if st.session_state.get("rol") not in roles:
        st.error("No tienes permisos")
        st.stop()
