import streamlit as st
from functools import wraps

# Supposez que votre fonction check_password ressemble à ceci :
def check_password():
    """Returns `True` if the user had a correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store password.
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password.
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error.
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Password incorrect")
        return False
    else:
        # Password correct.
        return True

# --- NOTRE NOUVEAU DÉCORATEUR ---
def secure_page(page_function):
    """
    Ceci est un décorateur. Il exécute la vérification du mot de passe
    AVANT d'exécuter la fonction de la page qu'il décore.
    """
    @wraps(page_function)
    def wrapper(*args, **kwargs):
        if not check_password():
            st.stop()  # Arrête l'exécution si le mot de passe n'est pas bon
        else:
            # Si le mot de passe est bon, exécute le code original de la page
            return page_function(*args, **kwargs)
    return wrapper
