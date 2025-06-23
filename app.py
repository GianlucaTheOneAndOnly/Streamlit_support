import streamlit as st
from password import check_password, add_logout_button

# --- Page Configuration (Must be the first Streamlit command) ---
st.set_page_config(
    page_title="Network Diagnostic Tool",
    page_icon="🛠️",
    layout="wide",
    initial_sidebar_state="collapsed"
)   

# --- Authentification ---
if not check_password():
    st.stop()


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
    ["Individual diagnostic", "Mass diagnostic", "Firmware Update", "iSee Hierachy"]
)

# --- Sidebar History Section ---
st.sidebar.title("⚙️ Actions & historic")

# --- Display Selected Page ---
if page == "Individual diagnostic":
    import individual_diagnostic
    individual_diagnostic.show()
elif page == "Mass diagnostic":
    import batch_diagnostic
    batch_diagnostic.show()
elif page == "Firmware Update":
    import csv_firmware
    csv_firmware.show()
elif page == "iSee Hierachy":
    import isee_page
    isee_page.show()

# --- History Display ---
with st.sidebar.expander("📜 Command history", expanded=False):
    if not st.session_state.command_history:
        st.write("Historic is empty.")
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
        if st.button("Delete history", key="clear_history"):
            st.session_state.command_history = []
            st.rerun()

        # Download history functionality
        import json
        history_json = json.dumps(st.session_state.command_history, indent=2)
        st.download_button(
            label="Download history (JSON)",
            data=history_json,
            file_name="command_history.json",
            mime="application/json",
            key="download_history"
        )

# --- CSV History in Sidebar (if applicable) ---
if page == "Generate CSV" and 'csv_history' in st.session_state and st.session_state.csv_history:
    with st.sidebar.expander("📄 History CSV", expanded=False):
        st.write(f"{len(st.session_state.csv_history)} file(s) generated")
        for i, csv_item in enumerate(st.session_state.csv_history[-3:]):  # Show last 3
            st.caption(f"📄 {csv_item['filename']} ({csv_item['urls_count']} URLs)")

st.sidebar.markdown("---")
st.sidebar.info("This app is for designed for remote diagnostic.")