import streamlit as st
import pandas as pd
import io
import json
import os

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
# You can use an absolute path like: "C:/Users/gianluca.carbone_ica/Desktop/streamlite/gateway_lookup.csv"
DEFAULT_LOOKUP_FILE = "gateway_lookup.csv"

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
        st.error(f"Erreur lors du chargement du fichier {file_path}: {str(e)}")
        return {}

def parse_lookup_csv(csv_data):
    """Parse CSV data into a dictionary mapping serial numbers to MAC addresses (lowercase)"""
    try:
        df = pd.read_csv(io.StringIO(csv_data))
        # Ensure required columns exist
        if 'serial_number' not in df.columns or 'mac_address' not in df.columns:
            st.error("Le fichier CSV doit contenir les colonnes 'serial_number' et 'mac_address'")
            return {}
        
        # Convert DataFrame to dictionary with lowercase MAC addresses
        lookup_dict = {}
        for _, row in df.iterrows():
            serial = str(row['serial_number']).strip()
            mac = str(row['mac_address']).strip().lower()  # Convert to lowercase
            lookup_dict[serial] = mac
        
        return lookup_dict
    except Exception as e:
        st.error(f"Erreur lors de l'analyse du CSV: {str(e)}")
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
        st.success(f"✅ Table de correspondance chargée depuis {DEFAULT_LOOKUP_FILE}")
        return file_lookup
    else:
        # Fall back to default data - show info about file location
        st.info(f"📁 Fichier `{DEFAULT_LOOKUP_FILE}` non trouvé. Utilisation de la table par défaut.")
        st.info(f"💡 Conseil: Placez votre fichier CSV dans: `{os.path.abspath(DEFAULT_LOOKUP_FILE)}`")
        return parse_lookup_csv(DEFAULT_LOOKUP_DATA)

def show():
    st.title("Diagnostic par Lots")
    st.markdown("Générez des commandes pour plusieurs gateways à la fois.")
    
    # Initialize session state for lookup table if not exists
    if 'lookup_table' not in st.session_state:
        st.session_state.lookup_table = initialize_lookup_table()
    
    # Add a button to reload from file
    if st.button("🔄 Recharger la table depuis le fichier"):
        file_lookup = load_lookup_from_file(DEFAULT_LOOKUP_FILE)
        if file_lookup:
            st.session_state.lookup_table = file_lookup
            st.success("Table de correspondance rechargée depuis le fichier!")
        else:
            st.warning("Impossible de recharger depuis le fichier, utilisation de la table actuelle")
    
    # --- Tabs for different input methods ---
    input_tab, lookup_tab = st.tabs(["Entrée des Gateways", "Table de Correspondance"])
    
    # --- Input Tab ---
    with input_tab:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            input_method = st.radio(
                "Méthode d'entrée:",
                ["Texte", "Fichier"],
                key="input_method"
            )
            
            gateway_list = []
            if input_method == "Texte":
                gateway_text = st.text_area(
                    "Liste des numéros de série des gateways (un par ligne):",
                    height=200,
                    placeholder="12345\n67890\n54321"
                )
                gateway_list = parse_gateway_list(gateway_text)
            else:
                uploaded_file = st.file_uploader(
                    "Télécharger un fichier texte avec les numéros de série (un par ligne):",
                    type=["txt"]
                )
                if uploaded_file is not None:
                    gateway_text = uploaded_file.getvalue().decode("utf-8")
                    gateway_list = parse_gateway_list(gateway_text)
        
        with col2:
            st.subheader("Commande à exécuter")
            command_options = [
                "sudo lwsalt list | grep {MAC}",
                "sudo lwsalt reset {MAC}",
                "sudo lwsalt neighbors {MAC}",
                "sudo lwsalt version {MAC}",
                "sudo salt {MAC} test.ping",
                "sudo salt '{MAC}' cmd.run 'reboot'",
                "Commande personnalisée"
            ]
            selected_command = st.selectbox(
                "Sélectionnez une commande à exécuter pour tous les gateways:",
                options=command_options,
                index=0
            )
            
            custom_command = ""
            if selected_command == "Commande personnalisée":
                custom_command = st.text_input(
                    "Entrez votre commande personnalisée:",
                    placeholder="sudo lwsalt custom {SERIAL} {MAC}",
                    help="Utilisez {SERIAL} pour le numéro de série et {MAC} pour l'adresse MAC"
                )
                command_template = custom_command
            else:
                command_template = selected_command

            st.info("Les macros {SERIAL} et {MAC} seront remplacées par les valeurs correspondantes. Les adresses MAC sont automatiquement converties en minuscules.")
            
        # Generate and display commands
        if gateway_list:
            st.subheader("Résultat des commandes")
            
            commands, missing = generate_commands(
                gateway_list, 
                st.session_state.lookup_table,
                command_template
            )
            
            # Show missing gateways
            if missing:
                st.warning(f"⚠️ {len(missing)} gateways non trouvées dans la table de correspondance: {', '.join(missing)}")
            
            # Display generated commands
            if commands:
                st.success(f"✅ {len(commands)} commandes générées")
                
                # Format for display and copy
                all_commands_text = "\n".join([cmd["command"] for cmd in commands])
                
                # Display commands in a code block
                st.markdown("<div class='multi-command-display'><strong>Commandes à exécuter:</strong></div>", unsafe_allow_html=True)
                st.code(all_commands_text, language="bash")
                
                # Add to history
                if st.button("Ajouter toutes les commandes à l'historique"):
                    for cmd in commands:
                        add_to_history(cmd["command"])
                    st.success(f"{len(commands)} commandes ajoutées à l'historique!")
                
                # Generate putty commands (for later use if needed)
                putty_cmds = []
                
                # Option to download as batch file
                st.download_button(
                    label="Télécharger comme fichier .bat",
                    data=all_commands_text,
                    file_name="gateway_commands.bat",
                    mime="text/plain"
                )
                
                # Display in table format for reference
                with st.expander("Voir les détails de chaque gateway"):
                    data = [{"Serial Number": cmd["serial"], "MAC Address": cmd["mac"], "Command": cmd["command"]} 
                            for cmd in commands]
                    st.table(data)
            else:
                st.info("Aucune commande n'a été générée. Vérifiez la table de correspondance.")
    
    # --- Lookup Table Tab ---
    with lookup_tab:
        st.subheader("Table de Correspondance Serial Number → MAC Address")
        
        # Display current file path info
        st.info(f"📁 Fichier de correspondance par défaut: `{DEFAULT_LOOKUP_FILE}`")
        st.info(f"📂 Chemin complet: `{os.path.abspath(DEFAULT_LOOKUP_FILE)}`")
        
        # Check if file exists
        if os.path.exists(DEFAULT_LOOKUP_FILE):
            st.success("✅ Fichier trouvé")
        else:
            st.warning("⚠️ Fichier non trouvé à cet emplacement")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            lookup_method = st.radio(
                "Méthode de mise à jour:",
                ["CSV Existant", "Télécharger CSV", "Éditer manuellement", "Recharger depuis fichier"],
                key="lookup_method"
            )
            
            csv_data = DEFAULT_LOOKUP_DATA
            
            if lookup_method == "Télécharger CSV":
                uploaded_csv = st.file_uploader(
                    "Télécharger un fichier CSV avec les colonnes 'serial_number' et 'mac_address':",
                    type=["csv"]
                )
                if uploaded_csv is not None:
                    csv_data = uploaded_csv.getvalue().decode("utf-8")
                    st.session_state.lookup_table = parse_lookup_csv(csv_data)
                    st.success("Table mise à jour depuis le fichier téléchargé!")
            
            elif lookup_method == "Éditer manuellement":
                csv_editor = st.text_area(
                    "Éditez le CSV (format: serial_number,mac_address):",
                    value=DEFAULT_LOOKUP_DATA,
                    height=200
                )
                if st.button("Mettre à jour la table"):
                    st.session_state.lookup_table = parse_lookup_csv(csv_editor)
                    st.success("Table de correspondance mise à jour!")
            
            elif lookup_method == "Recharger depuis fichier":
                st.markdown(f"**Fichier actuel:** `{DEFAULT_LOOKUP_FILE}`")
                st.markdown(f"**Chemin complet:** `{os.path.abspath(DEFAULT_LOOKUP_FILE)}`")
                
                if os.path.exists(DEFAULT_LOOKUP_FILE):
                    st.success("✅ Fichier trouvé")
                else:
                    st.warning("⚠️ Fichier non trouvé")
                
                if st.button("Recharger maintenant"):
                    file_lookup = load_lookup_from_file(DEFAULT_LOOKUP_FILE)
                    if file_lookup:
                        st.session_state.lookup_table = file_lookup
                        st.success("Table rechargée depuis le fichier!")
                    else:
                        st.error(f"Fichier introuvable à: {os.path.abspath(DEFAULT_LOOKUP_FILE)}")
        
        with col2:
            st.subheader("Aperçu de la table")
            lookup_df = pd.DataFrame(
                list(st.session_state.lookup_table.items()), 
                columns=["Numéro de Série", "Adresse MAC"]
            )
            st.dataframe(lookup_df)
            
            st.markdown("**Note:** Les adresses MAC sont automatiquement converties en minuscules")
            
            # Export current lookup table
            if st.button("Exporter la table actuelle"):
                lookup_csv = "serial_number,mac_address\n"
                for sn, mac in st.session_state.lookup_table.items():
                    lookup_csv += f"{sn},{mac}\n"
                
                st.download_button(
                    label="Télécharger le CSV",
                    data=lookup_csv,
                    file_name="gateway_lookup.csv",
                    mime="text/csv"
                )
            
            # Save current table to default file
            if st.button("💾 Sauvegarder comme fichier par défaut"):
                try:
                    lookup_csv = "serial_number,mac_address\n"
                    for sn, mac in st.session_state.lookup_table.items():
                        lookup_csv += f"{sn},{mac}\n"
                    
                    with open(DEFAULT_LOOKUP_FILE, 'w', encoding='utf-8') as f:
                        f.write(lookup_csv)
                    
                    st.success(f"Table sauvegardée dans {DEFAULT_LOOKUP_FILE}")
                except Exception as e:
                    st.error(f"Erreur lors de la sauvegarde: {str(e)}")