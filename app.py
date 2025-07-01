import streamlit as st
import json
from streamlit.components.v1 import html
from src.auth import check_password

# --- Page Configuration (Must be the first Streamlit command) ---
st.set_page_config(
    page_title="Diagnostic Tool - Home",
    page_icon="🛠️",
    layout="wide",
    initial_sidebar_state="auto"
)

# --- Authentication ---
# This check protects the entire app. If it fails, the script stops here.
if not check_password():
    st.stop()

# --- Apply Custom Global Styling ---
# This CSS is injected into every page.
st.markdown("""
<style>
    /* Main headers */
    h1, h2 {
        color: #1e88e5; /* A nice blue color */
        border-bottom: 2px solid #eef2f6; /* A light separator line */
        padding-bottom: 0.5rem;
    }
    /* Style for the navigation cards on the homepage */
    .nav-card {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 0.5rem;
        padding: 1rem;
        text-align: center;
        transition: transform 0.2s;
    }
    .nav-card:hover {
        transform: scale(1.03);
        border-color: #1e88e5;
    }
</style>
""", unsafe_allow_html=True)


def display_homepage():
    """Renders the main content of the homepage."""
    st.title("Welcome to the Network Diagnostic Tool")
    st.markdown("---")
    st.header("How to Use This Application")
    st.info("👈 **Select a tool from the sidebar** or use one of the quick access panels below to get started.")

    st.markdown("This application provides several modules to help you diagnose network issues and manage devices.")
    st.markdown("### Available Tools:")

    # --- Interactive Navigation using st.page_link in columns ---
    col1, col2 = st.columns(2)

    with col1:
        st.page_link(
            "pages/1_Individual_Diagnostic.py",
            label="### Individual Diagnostic",
            icon="🎯"
        )
        st.markdown("Run commands on a single device by its UID.")

        st.page_link(
            "pages/3_Firmware_update.py", # Assuming this is the correct path
            label="### Firmware Update",
            icon="⬆️"
        )
        st.markdown("Generate firmware update files for devices.")

    with col2:
        st.page_link(
            "pages/2_Batch_Diagnostic.py", # Assuming this is the correct path
            label="### Mass Diagnostic",
            icon="🚀"
        )
        st.markdown("Execute commands on a list of devices simultaneously.")

        st.page_link(
            "pages/4_Download_Hierarchy.py",
            label="### iSee Hierarchy",
            icon="📂"
        )
        st.markdown("Explore and download the asset hierarchy.")


def display_sidebar():
    """Renders the global sidebar content for all pages."""
    with st.sidebar:
        st.title("⚙️ Actions & History")

        # History Display in the sidebar
        with st.expander("📜 Command History", expanded=True):
            if not st.session_state.get('command_history', []):
                st.write("History is empty.")
            else:
                # Display history commands
                for cmd in st.session_state.command_history:
                    st.code(cmd, language='bash')
                
                st.markdown("---") # Separator

                # Clear History button
                if st.button("Clear History", key="clear_history"):
                    st.session_state.command_history = []
                    st.rerun()

                # Download history functionality
                history_json = json.dumps(st.session_state.command_history, indent=2)
                st.download_button(
                    label="Download History (JSON)",
                    data=history_json,
                    file_name="command_history.json",
                    mime="application/json",
                    key="download_history"
                )

        st.markdown("---")

        # --- Functional Logout Button ---
        if st.button("Logout"):
            st.session_state["password_correct"] = False
            st.rerun()

        st.info("Application for remote diagnostics.")

# --- Main App Execution ---
display_homepage()
display_sidebar()