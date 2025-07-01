import streamlit as st
import json
from src.auth import check_password # Assuming you have a logout function here too

# --- Page Configuration (Must be the first Streamlit command) ---
# This config applies to all pages
st.set_page_config(
    page_title="Accueil - Outil de Diagnostic",
    page_icon="🛠️",
    layout="wide",
    initial_sidebar_state="auto" # 'auto' is often better than 'collapsed'
)

# --- Authentication ---
# This will run before any page is displayed, protecting the whole app.
if not check_password():
    st.stop()

# --- Apply Custom Global Styling ---
# This CSS will be injected into every page automatically.
st.markdown("""
<style>
    /* Make headers closer to the original */
    h1, h2 {
        color: #1e88e5; /* --primary-color */
        border-bottom: 2px solid #e3f2fd; /* --secondary-color */
        padding-bottom: 0.5rem;
    }
    .stButton>button {
        /* General button styling can go here */
    }
    /* ... (keep all your other CSS classes like .command-item-container, etc.) ... */
    .uid-command-display {
        padding: 1rem;
        background-color: #f8f9fa;
        border-left: 4px solid #1e88e5;
        font-family: monospace;
        font-size: 1.1rem;
        word-break: break-all;
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)


# --- Initialize Session State (if not already done) ---
if 'command_history' not in st.session_state:
    st.session_state.command_history = []

# --- Main Homepage Content ---
# This is what users will see when they first land on your app.
st.title("Bienvenue sur l'Outil de Diagnostic Réseau")
st.markdown("---")
st.header("Comment utiliser cette application :")
st.info("👈 **Veuillez sélectionner un outil dans le menu de navigation** qui est apparu dans la barre latérale pour commencer.")

st.markdown("""
Cette application fournit plusieurs modules pour vous aider à diagnostiquer les problèmes de réseau et à gérer les appareils.

### Outils Disponibles:
- **Individual diagnostic:** Pour lancer des commandes sur un seul appareil.
- **Mass diagnostic:** Pour exécuter des commandes sur une liste d'appareils.
- **Firmware Update:** Pour générer des fichiers de mise à jour.
- **iSee Hierarchy:** Pour explorer et télécharger la hiérarchie des appareils.
""")


# --- Global Sidebar Elements ---
# Everything in the sidebar here will appear on ALL pages.
st.sidebar.title("⚙️ Actions & Historique")

# History Display in the sidebar
with st.sidebar.expander("📜 Historique des commandes", expanded=False):
    if not st.session_state.command_history:
        st.write("L'historique est vide.")
    else:
        # Display history in reverse for recent commands first
        for j, hist_cmd in enumerate(reversed(st.session_state.command_history)):
            st.code(hist_cmd, language='bash')
            st.caption(f"Commande {len(st.session_state.command_history) - j}")
            st.markdown("---")

    if st.session_state.command_history:
        if st.button("Effacer l'historique", key="clear_history"):
            st.session_state.command_history = []
            st.rerun()

        # Download history functionality
        history_json = json.dumps(st.session_state.command_history, indent=2)
        st.download_button(
            label="Télécharger l'historique (JSON)",
            data=history_json,
            file_name="command_history.json",
            mime="application/json",
            key="download_history"
        )

st.sidebar.markdown("---")
st.sidebar.info("Application pour le diagnostic à distance.")
# If you have a logout button function, you can call it here
# add_logout_button()

