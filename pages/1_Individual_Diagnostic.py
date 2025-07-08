import streamlit as st
import base64
from src.auth import secure_page

# --- Initialize session state ---
if 'command_history' not in st.session_state:
    st.session_state.command_history = []

# --- Command Data (All descriptions translated to English) ---
commands_data = [
    {
        "text": "sudo lwsalt list | grep UID", "type": "NEXT", "category": "G23",
        "description": "Ping (check presence via lwsalt list)"
    },
    {
        "text": "sudo lwsalt neighbors UID", "type": "NEXT", "category": "G23",
        "description": "Show network type, RSSI, and network info"
    },
    {
        "text": "sudo lwsalt reset UID", "type": "NEXT", "category": "G23",
        "description": "Reset the gateway"
    },
    {
        "text": "sudo lwsalt version UID", "type": "NEXT", "category": "G23",
        "description": "Show the current firmware version"
    },
    {
        "text": "sudo lwsalt settings UID", "type": "NEXT", "category": "G23",
        "description": "Display the current settings"
    },
    {
        "text": "sudo lwsalt sensors UID", "type": "NEXT", "category": "G23",
        "description": "Display the sensors linked to this gateway"
    },
    {
        "text": "sudo lwsalt network UID", "type": "NEXT", "category": "G23",
        "description": "Display the network IF the gateway is a leader"
    },
    {
        "text": "sudo lwsalt rssi UID", "type": "NEXT", "category": "G23",
        "description": "Display the RSSI"
    },
    {
        "text": "sudo lwsalt enterinstallmode UID", "type": "NEXT", "category": "G23",
        "description": "Set the gateway to install mode for 8 hours"
    },
    {
        "text": "sudo salt UID cmd.run 'reboot'", "type": "OLD", "category": "OLD GEN",
        "description": "Reset the gateway (use with UID)"
    },
    {
        "text": "sudo salt-key", "type": "OLD", "category": "OLD GEN",
        "description": "Return the list of all active gateways"
    },
    {
        "text": "sudo salt UID test.ping", "type": "OLD", "category": "OLD GEN",
        "description": "Ping the gateway"
    },
    {
        "text": "sudo salt UID cmd.run 'dh-h", "type": "OLD", "category": "OLD GEN",
        "description": "Check available memory"
    },
    {
        "text": "sudo salt UID cmd.run 'cat/etc/wicare.ini'", "type": "OLD", "category": "OLD GEN",
        "description": "Check wicare.ini"
    },
    {
        "text": "sudo salt UID cmd.run 'date'", "type": "OLD", "category": "OLD GEN",
        "description": "Set current date"
    },
    {
        "text": "sudo salt UID cmd.run 'systemctl status wicare_gateway'", "type": "OLD", "category": "OLD GEN",
        "description": "Check service status gateway"
    },
    {
        "text": "sudo salt UID cmd.run 'systemctl status wicare_coordinator'", "type": "OLD", "category": "OLD GEN",
        "description": "Check service status coordinator"
    },
    {
        "text": "sudo salt UID cmd.run ' ' journalctl -u wicare_coordinator --since=\"2 minute ago\" '", "type": "OLD", "category": "OLD GEN",
        "description": "Check coordinator log in a given time interval"
    },
    {
        "text": "sudo salt UID cmd.run ' journalctl -u wicare_coordinator --since \"AAAA-MM-JJ hh:mm\" -- until \"AAAA-MM-JJ hh:mm\" '", "type": "OLD", "category": "OLD GEN",
        "description": "Check coordinator log in a given time interval"
    },
    {
        "text": "sudo salt UID cmd.run \"/opt/wicare_gateway --version\"", "type": "OLD", "category": "Advantech",
        "description": "Check gateway firmware version"
    },
    {
        "text": "sudo salt UID state.sls update_advantech saltenv=prod", "type": "OLD", "category": "Advantech",
        "description": "Push new firmware version"
    },
    {
        "text": "sudo salt UID cmd.run 'cat /usr/local/lib/python*/site-packages/gatewayversion.py'", "type": "OLD", "category": "BLUE_SEED",
        "description": "Check gateway version"
    },
    {
        "text": "sudo salt UID  cmd.run 'rauc install ", "type": "OLD", "category": "BLUE_SEED",
        "description": "Push new firmware (if current is older than 2.1.4.0)"
    },
    {
        "text": "sudo salt -t 3600 UID  cmd.run 'rauc install ", "type": "OLD", "category": "BLUE_SEED",
        "description": "Push new firmware (if current is equal or newer than 2.1.4.0)"
    }



]

# --- Helper Functions ---
def get_category_name(category_code):
    name_map = {
        "Advantech": "Specific Advantech",
        "BLUE_SEED": "Specific BLUE/SEED",
        "G23": "G23",
        "OLD GEN" : "OLD GEN"
    }
    return name_map.get(category_code, category_code)

def add_to_history(command_text):
    """Adds a command to the history, avoiding duplicates and limiting size."""
    # Move command to top if it already exists
    if command_text in st.session_state.command_history:
        st.session_state.command_history.remove(command_text)
    st.session_state.command_history.insert(0, command_text)
    # Limit history to 20 items
    while len(st.session_state.command_history) > 20:
        st.session_state.command_history.pop()

def get_download_link(text_to_download, filename, link_text):
    """Generates a link to download the given text as a file."""
    b64 = base64.b64encode(text_to_download.encode()).decode()
    return f'<a href="data:file/txt;base64,{b64}" download="{filename}">{link_text}</a>'

@secure_page
def render_individual_diag():
    st.title("Individual Device Diagnostic")
    st.markdown("Enter a device UID to generate and run diagnostic commands.")

    # --- Inputs in a more compact sidebar ---
    with st.sidebar:
        st.header("Filters")
        router_type_options = ["all", "OLD", "NEXT"]
        selected_router_type = st.selectbox(
            "Equipment Type:",
            options=router_type_options,
            index=0,
            key="router_type_filter"
        )

        uid_input = st.text_input(
            "Unique Identifier (UID):",
            placeholder="e.g., 1234-ABC",
            help="The UID will be automatically integrated into commands where 'UID' is present."
        ).strip()
        
        search_query = st.text_input(
            "Filter commands by keyword:",
            placeholder="e.g., reset, version, network..."
        ).lower()

    # --- Main Page Layout ---
    st.subheader("Available Commands")

    # --- Command Tabs ---
    categories = ["all"] + sorted(list(set(cmd["category"] for cmd in commands_data)))
    tab_titles = [get_category_name(cat) if cat != "all" else "All" for cat in categories]
    selected_tabs = st.tabs(tab_titles)

    for i, tab in enumerate(selected_tabs):
        with tab:
            current_tab_category = categories[i]
            
            # --- Filtering Logic ---
            filtered_commands = []
            for cmd in commands_data:
                type_match = (selected_router_type == 'all' or cmd['type'] == 'all' or cmd['type'] == selected_router_type)
                category_match = (current_tab_category == 'all' or cmd['category'] == current_tab_category)
                search_match = (search_query in cmd['text'].lower() or search_query in cmd['description'].lower())
                
                if type_match and category_match and search_match:
                    final_cmd_text = cmd['text'].replace("UID", uid_input) if uid_input else cmd['text']
                    filtered_commands.append({**cmd, "processed_text": final_cmd_text})

            # --- Display Commands using Expanders ---
            if not filtered_commands:
                st.info("No commands match your current filter criteria in this category.")
            else:
                for idx, command in enumerate(filtered_commands):
                    expander_title = f"{command['description']}"
                    with st.expander(expander_title):
                        st.code(command['processed_text'], language='bash')
                        if st.button("Add to History", key=f"history_{current_tab_category}_{idx}"):
                            add_to_history(command['processed_text'])
                            st.success(f"Added '{command['description']}' to history.")
                            st.rerun()

    st.markdown("---")

    # --- Command History Section ---
    st.subheader("Command History")

    if st.session_state.command_history:
        # --- NEW: Clear History Button ---
        if st.button("Clear History"):
            st.session_state.command_history.clear()
            st.rerun()

        # Display history commands
        for command_text in st.session_state.command_history:
            st.code(command_text, language='bash')

        # Prepare history for download
        history_text = "\n".join(st.session_state.command_history)
        st.markdown(
            get_download_link(history_text, "command_history.txt", "Download Command History (.txt)"),
            unsafe_allow_html=True
        )
    else:
        st.info("Your command history is empty. Add commands to see them here.")

render_individual_diag()