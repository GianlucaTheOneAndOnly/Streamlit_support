# password.py
import streamlit as st

# --- STYLE LOGIN POUR EFFET "POP-UP" ---
LOGIN_STYLE = """
<style>
    .login-box {
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background-color: white;
        padding: 3rem;
        border-radius: 10px;
        box-shadow: 0 0 20px rgba(0,0,0,0.1);
        z-index: 9999;
        width: 100%;
        max-width: 400px;
    }
    .stApp {
        filter: blur(4px);
    }
</style>
"""

# --- FONCTION À IMPORTER ---
def check_password():
    """Affiche un écran de connexion tant que l'utilisateur n'est pas authentifié."""

    def password_entered():
        """Vérifie si le mot de passe est correct et met à jour la session."""
        if st.session_state["password"] in st.secrets["passwords"].values():
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Supprime le mot de passe pour la sécurité
        else:
            st.session_state["password_correct"] = False

    # Si déjà authentifié
    if st.session_state.get("password_correct", False):
        return True

    # Sinon : afficher l'écran de connexion
    st.markdown(LOGIN_STYLE, unsafe_allow_html=True)
    with st.container():
        login_box = st.container()
        with login_box:
            st.markdown('<div class="login-box">', unsafe_allow_html=True)
            st.header("🔐 Connexion requise")
            st.text_input("Mot de passe", type="password", on_change=password_entered, key="password")
            if "password_correct" in st.session_state and not st.session_state["password_correct"]:
                st.error("Mot de passe incorrect.")
            st.markdown('</div>', unsafe_allow_html=True)

    # Stoppe le rendu tant que pas connecté
    st.stop()
