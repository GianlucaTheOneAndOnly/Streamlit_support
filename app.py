import streamlit as st

# --- Page Configuration (Must be the first Streamlit command) ---
st.set_page_config(
    page_title="Outil de Diagnostic Réseau",
    page_icon="🛠️",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# Fonction pour vérifier le mot de passe
def check_password():
    """Retourne True si l'utilisateur a entré un mot de passe valide."""

    def password_entered():
        """Vérifie si le mot de passe entré par l'utilisateur est correct."""
        if st.session_state["password"] in st.secrets["passwords"].values():
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Ne pas garder le mot de passe en mémoire
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # Première exécution, initialiser l'état.
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Mot de passe incorrect, redemander.
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Password incorrect")
        return False
    else:
        # Mot de passe correct.
        return True

# --- Début de votre application ---

if check_password():
    # Mettez TOUT le reste de votre code d'application ici.
    # Par exemple :
    st.title("Bienvenue sur l'App de Diagnostic !")
    st.write("Vous êtes connecté.")
    
    # ... le reste de votre code (st.file_uploader, vos fonctions, etc.)


# --- Apply Custom Styling ---
st.markdown("""
<style>
    /* Make headers closer to the original */
    h1, h2 {
        color: #1e88e5; /* --primary-color */
        border-bottom: 2px solid #e3f2fd; /* --secondary-color */
        padding-bottom: 0.5rem;
    }
    .stButton>button {
        /* You can add some general button styling here if needed */
        /* For specific buttons, you might need more targeted selectors or use st.columns for layout */
    }
    .command-item-container {
        border: 1px solid #ddd;
        border-radius: 4px; /* --border-radius */
        padding: 0.75rem 1rem;
        margin-bottom: 0.5rem;
        background-color: #fff;
    }
    .command-item-container:hover {
        background-color: #e3f2fd; /* --secondary-color */
    }
    .command-desc {
        font-size: 0.85rem;
        color: #666;
        margin-top: 0.25rem;
    }
    .command-category-badge {
        display: inline-block;
        font-size: 0.75rem;
        background-color: #e3f2fd; /* --secondary-color */
        color: #1e88e5; /* --primary-color */
        padding: 0.2rem 0.5rem;
        border-radius: 10px;
        margin-right: 0.5rem;
    }
    .uid-command-display {
        padding: 1rem;
        background-color: #f8f9fa;
        border-left: 4px solid #1e88e5; /* --primary-color */
        font-family: monospace;
        font-size: 1.1rem; /* Adjusted for st.code consistency */
        word-break: break-all;
        margin-bottom: 0.5rem;
    }
    .multi-command-display {
        padding: 1rem;
        background-color: #f5f5f5;
        border-left: 4px solid #43a047; /* Green highlight for batch commands */
        font-family: monospace;
        font-size: 1rem;
        word-break: break-all;
        margin-bottom: 0.5rem;
    }
    /* Styling for CSV generator */
    .csv-preview {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 0.375rem;
        padding: 1rem;
        font-family: monospace;
    }
</style>
""", unsafe_allow_html=True)

# --- Initialize Session State ---
if 'command_history' not in st.session_state:
    st.session_state.command_history = []

# --- Page Navigation ---
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Sélectionner une page:", 
    ["Diagnostic Individuel", "Diagnostic par Lots", "Générateur CSV"]
)

# --- Sidebar History Section ---
st.sidebar.title("⚙️ Actions & Historique")

# --- Display Selected Page ---
if page == "Diagnostic Individuel":
    import individual_diagnostic
    individual_diagnostic.show()
elif page == "Diagnostic par Lots":
    import batch_diagnostic
    batch_diagnostic.show()
else:  # Générateur CSV
    import csv_generator
    csv_generator.show()

# --- History Display ---
with st.sidebar.expander("📜 Historique des commandes copiées/préparées", expanded=False):
    if not st.session_state.command_history:
        st.write("L'historique est vide.")
    else:
        for j, hist_cmd in enumerate(st.session_state.command_history):
            st.code(hist_cmd, language='bash')
            if st.button("Renvoyer cette commande", key=f"hist_copy_{j}", help="Cliquez pour copier de nouveau (utilise le bouton de copie du bloc de code)."):
                 # No action needed other than user clicking st.code's copy button.
                 # Potentially re-add to top of history if desired.
                 st.info("Utilisez l'icône de copie sur le bloc de code ci-dessus.")
            st.caption(f"Commande {j+1}")
            st.markdown("---")

    if st.session_state.command_history:
        if st.button("Effacer l'historique", key="clear_history"):
            st.session_state.command_history = []
            st.rerun()

        # Download history functionality
        import json
        history_json = json.dumps(st.session_state.command_history, indent=2)
        st.download_button(
            label="Télécharger l'historique (JSON)",
            data=history_json,
            file_name="command_history.json",
            mime="application/json",
            key="download_history"
        )

# --- CSV History in Sidebar (if applicable) ---
if page == "Générateur CSV" and 'csv_history' in st.session_state and st.session_state.csv_history:
    with st.sidebar.expander("📄 Historique CSV", expanded=False):
        st.write(f"{len(st.session_state.csv_history)} fichier(s) généré(s)")
        for i, csv_item in enumerate(st.session_state.csv_history[-3:]):  # Show last 3
            st.caption(f"📄 {csv_item['filename']} ({csv_item['urls_count']} URLs)")

st.sidebar.markdown("---")
st.sidebar.info("Cette application est un outil de diagnostic réseau pour les gateways.")