import streamlit as st
from logic import asegurar_sesion, cambiar_password

asegurar_sesion()

if not st.session_state.autenticado:
    st.switch_page("app.py")
    st.stop()

st.set_page_config(page_title="Mi Cuenta", layout="centered")
st.title("🔐 Mi Cuenta")

st.write(f"Usuario: **{st.session_state.usuario}**")

st.subheader("Cambiar contraseña")

p1 = st.text_input("Nueva contraseña", type="password")
p2 = st.text_input("Confirmar contraseña", type="password")

if st.button("Actualizar contraseña"):
    if not p1 or not p2:
        st.warning("Completa ambos campos")
    elif p1 != p2:
        st.error("No coinciden")
    else:
        cambiar_password(st.session_state.user_id, p1)
        st.success("Contraseña actualizada")
