import streamlit as st
import pandas as pd
import io
import json
import os
from src.auth import secure_page


# --- Lookup Table for Gateway SN to MAC Address ---
# In a real application, this would be loaded from a database or file
# For this example, we'll create a simple dictionary
DEFAULT_LOOKUP_DATA = """
serial_number,mac_address
12345,00:11:22:33:44:55
67890,AA:BB:CC:DD:EE:FF
54321,11:22:33:44:55:66
98765,AA:BB:CC:11:22:33
TEST001,00:00:11:22:33:44
"""

# Default file path for lookup table (modify this path as needed)
# You can use an absolute path like: "C:/Users/your_user/Desktop/streamlit_app/gateway_lookup.csv"
DEFAULT_LOOKUP_FILE = "data/gateway_lookup.csv"

# --- Helper Functions ---
def add_to_history(command_text):
    if command_text not in st.session_state.command_history:
        st.session_state.command_history.insert(0, command_text)
        if len(st.session_state.command_history) > 20:  # Limit history
            st.session_state.command_history.pop()

def parse_gateway_list(text_input):
    """Parse text input into a list of gateway serial numbers"""
    if not text_input:
        return []
    
    lines = text_input.strip().split('\n')
    # Remove empty lines and trim whitespace
    gateways = [line.strip() for line in lines if line.strip()]
    return gateways

def load_lookup_from_file(file_path):
    """Load lookup table from a CSV file"""
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                csv_data = f.read()
            return parse_lookup_csv(csv_data)
        else:
            # Don't show info message during initialization, only when explicitly requested
            return {}
    except Exception as e:
        st.error(f"Error while loading file {file_path}: {str(e)}")
        return {}

def parse_lookup_csv(csv_data):
    """Parse CSV data into a dictionary mapping serial numbers to MAC addresses (lowercase)"""
    try:
        df = pd.read_csv(io.StringIO(csv_data))
        # Ensure required columns exist
        if 'serial_number' not in df.columns or 'mac_address' not in df.columns:
            st.error("The CSV file must contain the columns 'serial_number' and 'mac_address'")
            return {}
        
        # Convert DataFrame to dictionary with lowercase MAC addresses
        lookup_dict = {}
        for _, row in df.iterrows():
            serial = str(row['serial_number']).strip()
            mac = str(row['mac_address']).strip().lower()  # Convert to lowercase
            lookup_dict[serial] = mac
        
        return lookup_dict
    except Exception as e:
        st.error(f"Error while parsing the CSV: {str(e)}")
        return {}

def generate_commands(gateways, lookup_table, command_template):
    """Generate commands for each gateway"""
    commands = []
    missing_gateways = []
    
    for gateway in gateways:
        if gateway in lookup_table:
            mac = lookup_table[gateway]  # MAC is already in lowercase from parse_lookup_csv
            # Replace placeholders in command template
            cmd = command_template.replace("{SERIAL}", gateway).replace("{MAC}", mac)
            commands.append({"serial": gateway, "mac": mac, "command": cmd})
        else:
            missing_gateways.append(gateway)
    
    return commands, missing_gateways

def initialize_lookup_table():
    """Initialize the lookup table from file or default data"""
    # Try to load from default file first
    file_lookup = load_lookup_from_file(DEFAULT_LOOKUP_FILE)
    
    if file_lookup:
        st.success(f"✅ Lookup table loaded from {DEFAULT_LOOKUP_FILE}")
        return file_lookup
    else:
        # Fall back to default data - show info about file location
        st.info(f"📁 File `{DEFAULT_LOOKUP_FILE}` not found. Using the default table.")
        st.info(f"💡 Tip: Place your CSV file in: `{os.path.abspath(DEFAULT_LOOKUP_FILE)}`")
        return parse_lookup_csv(DEFAULT_LOOKUP_DATA)

@secure_page
def render_batch_diagnostic():

    st.title("Batch Diagnostic")
    st.markdown("Generate commands for multiple gateways at once.")

    # Initialize session state for lookup table if not exists
    if 'lookup_table' not in st.session_state:
        st.session_state.lookup_table = initialize_lookup_table()

    # Add a button to reload from file
    if st.button("🔄 Reload table from file"):
        file_lookup = load_lookup_from_file(DEFAULT_LOOKUP_FILE)
        if file_lookup:
            st.session_state.lookup_table = file_lookup
            st.success("Lookup table reloaded from file!")
        else:
            st.warning("Could not reload from file, using the current table")

    # --- Tabs for different input methods ---
    input_tab, lookup_tab = st.tabs(["Gateway Input", "Lookup Table"])

    # --- Input Tab ---
    with input_tab:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            input_method = st.radio(
                "Input method:",
                ["Text", "File"],
                key="input_method"
            )
            
            gateway_list = []
            if input_method == "Text":
                gateway_text = st.text_area(
                    "List of gateway serial numbers (one per line):",
                    height=200,
                    placeholder="12345\n67890\n54321"
                )
                gateway_list = parse_gateway_list(gateway_text)
            else:
                uploaded_file = st.file_uploader(
                    "Upload a text file with serial numbers (one per line):",
                    type=["txt"]
                )
                if uploaded_file is not None:
                    gateway_text = uploaded_file.getvalue().decode("utf-8")
                    gateway_list = parse_gateway_list(gateway_text)
        
        with col2:
            st.subheader("Command to execute")
            command_options = [
                "sudo lwsalt list | grep {MAC}",
                "sudo lwsalt reset {MAC}",
                "sudo lwsalt neighbors {MAC}",
                "sudo lwsalt network {MAC}",
                "sudo lwsalt version {MAC}",
                "sudo lwsalt rssi {MAC}",
                "Custom command"
            ]
            selected_command = st.selectbox(
                "Select a command to execute for all gateways:",
                options=command_options,
                index=0
            )
            
            custom_command = ""
            if selected_command == "Custom command":
                custom_command = st.text_input(
                    "Enter your custom command:",
                    placeholder="sudo lwsalt custom {SERIAL} {MAC}",
                    help="Use {SERIAL} for the serial number and {MAC} for the MAC address"
                )
                command_template = custom_command
            else:
                command_template = selected_command

            st.info("The {SERIAL} and {MAC} macros will be replaced with the corresponding values. MAC addresses are automatically converted to lowercase.")
            
        # Generate and display commands
        if gateway_list:
            st.subheader("Command Results")
            
            commands, missing = generate_commands(
                gateway_list, 
                st.session_state.lookup_table,
                command_template
            )
            
            # Show missing gateways
            if missing:
                st.warning(f"⚠️ {len(missing)} gateways not found in the lookup table: {', '.join(missing)}")
            
            # Display generated commands
            if commands:
                st.success(f"✅ {len(commands)} commands generated")
                
                # Format for display and copy
                all_commands_text = "\n".join([cmd["command"] for cmd in commands])
                
                # Display commands in a code block
                st.markdown("<div class='multi-command-display'><strong>Commands to execute:</strong></div>", unsafe_allow_html=True)
                st.code(all_commands_text, language="bash")
                
                # Add to history
                if st.button("Add all commands to history"):
                    for cmd in commands:
                        add_to_history(cmd["command"])
                    st.success(f"{len(commands)} commands added to history!")
                
                # Generate putty commands (for later use if needed)
                putty_cmds = []
                
                # Option to download as batch file
                st.download_button(
                    label="Download as .bat file",
                    data=all_commands_text,
                    file_name="gateway_commands.bat",
                    mime="text/plain"
                )
                
                # Display in table format for reference
                with st.expander("See details for each gateway"):
                    data = [{"Serial Number": cmd["serial"], "MAC Address": cmd["mac"], "Command": cmd["command"]} 
                            for cmd in commands]
                    st.table(data)
            else:
                st.info("No commands were generated. Check the lookup table.")

    # --- Lookup Table Tab ---
    with lookup_tab:
        st.subheader("Serial Number → MAC Address Lookup Table")
        
        # Display current file path info
        st.info(f"📁 Default lookup file: `{DEFAULT_LOOKUP_FILE}`")
        st.info(f"📂 Full path: `{os.path.abspath(DEFAULT_LOOKUP_FILE)}`")
        
        # Check if file exists
        if os.path.exists(DEFAULT_LOOKUP_FILE):
            st.success("✅ File found")
        else:
            st.warning("⚠️ File not found at this location")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            lookup_method = st.radio(
                "Update method:",
                ["Existing CSV", "Upload CSV", "Edit manually", "Reload from file"],
                key="lookup_method"
            )
            
            csv_data = DEFAULT_LOOKUP_DATA
            
            if lookup_method == "Upload CSV":
                uploaded_csv = st.file_uploader(
                    "Upload a CSV file with 'serial_number' and 'mac_address' columns:",
                    type=["csv"]
                )
                if uploaded_csv is not None:
                    csv_data = uploaded_csv.getvalue().decode("utf-8")
                    st.session_state.lookup_table = parse_lookup_csv(csv_data)
                    st.success("Table updated from the uploaded file!")
            
            elif lookup_method == "Edit manually":
                csv_editor = st.text_area(
                    "Edit the CSV (format: serial_number,mac_address):",
                    value=DEFAULT_LOOKUP_DATA,
                    height=200
                )
                if st.button("Update table"):
                    st.session_state.lookup_table = parse_lookup_csv(csv_editor)
                    st.success("Lookup table updated!")
            
            elif lookup_method == "Reload from file":
                st.markdown(f"**Current file:** `{DEFAULT_LOOKUP_FILE}`")
                st.markdown(f"**Full path:** `{os.path.abspath(DEFAULT_LOOKUP_FILE)}`")
                
                if os.path.exists(DEFAULT_LOOKUP_FILE):
                    st.success("✅ File found")
                else:
                    st.warning("⚠️ File not found")
                
                if st.button("Reload now"):
                    file_lookup = load_lookup_from_file(DEFAULT_LOOKUP_FILE)
                    if file_lookup:
                        st.session_state.lookup_table = file_lookup
                        st.success("Table reloaded from file!")
                    else:
                        st.error(f"File not found at: {os.path.abspath(DEFAULT_LOOKUP_FILE)}")
        
        with col2:
            st.subheader("Table Preview")
            lookup_df = pd.DataFrame(
                list(st.session_state.lookup_table.items()), 
                columns=["Serial Number", "MAC Address"]
            )
            st.dataframe(lookup_df)
            
            st.markdown("**Note:** MAC addresses are automatically converted to lowercase")
            
            # Export current lookup table
            if st.button("Export current table"):
                lookup_csv = "serial_number,mac_address\n"
                for sn, mac in st.session_state.lookup_table.items():
                    lookup_csv += f"{sn},{mac}\n"
                
                st.download_button(
                    label="Download CSV",
                    data=lookup_csv,
                    file_name="gateway_lookup.csv",
                    mime="text/csv"
                )
            
            # Save current table to default file
            if st.button("💾 Save as default file"):
                try:
                    lookup_csv = "serial_number,mac_address\n"
                    for sn, mac in st.session_state.lookup_table.items():
                        lookup_csv += f"{sn},{mac}\n"
                    
                    with open(DEFAULT_LOOKUP_FILE, 'w', encoding='utf-8') as f:
                        f.write(lookup_csv)
                    
                    st.success(f"Table saved to {DEFAULT_LOOKUP_FILE}")
                except Exception as e:
                    st.error(f"Error while saving: {str(e)}")

render_batch_diagnostic()