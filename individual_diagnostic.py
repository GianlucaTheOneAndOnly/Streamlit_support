import streamlit as st
import json

# --- Command Data ---
commands_data = [
    {
        "text": "sudo lwsalt list | grep UID", "type": "NEXT", "category": "G23",
        "description": "Ping (vérifie la présence via lwsalt list)"
    },
    {
        "text": "sudo lwsalt neighbors UID", "type": "NEXT", "category": "G23",
        "description": "Type de réseau, RSSI et infos réseau"
    },
    {
        "text": "sudo lwsalt reset UID", "type": "NEXT", "category": "G23",
        "description": "Reset la gateway"
    },
    {
        "text": "sudo lwsalt version UID", "type": "NEXT", "category": "G23",
        "description": "Version actuelle du firmware"
    },
    {
        "text": "sudo lwsalt settings UID", "type": "NEXT", "category": "G23",
        "description": "Affiche les paramètres actuels"
    },
    {
        "text": "sudo lwsalt sensors UID", "type": "NEXT", "category": "G23",
        "description": "Affiche les capteurs liés à cette gateway"
    },
    {
        "text": "sudo lwsalt network UID", "type": "NEXT", "category": "G23",
        "description": "Affiche le réseau SI la gateway est leader"
    },
    {
        "text": "sudo lwsalt rssi UID", "type": "NEXT", "category": "G23",
        "description": "Affiche le RSSI"
    },
    {
        "text": "sudo lwsalt enterinstallmode UID", "type": "NEXT", "category": "G23",
        "description": "Passe la gateway en install mode pour 8 heures"
    },
    {
        "text": "show configuration | display set UID", "type": "NEXT", "category": "Advantech",
        "description": "Affiche la configuration sous forme de commandes set"
    },
    {
        "text": "display current-configuration UID", "type": "OLD", "category": "Advantech",
        "description": "Affiche la configuration active de l'équipement"
    },
    {
        "text": "ping 8.8.8.8 source vlan 1 UID", "type": "OLD", "category": "G23",
        "description": "Teste la connectivité Internet en utilisant l'interface VLAN 1"
    },
    {
        "text": "display interface brief UID", "type": "NEXT", "category": "G23",
        "description": "Affiche un résumé de l'état des interfaces"
    },
    {
        "text": "display device UID", "type": "NEXT", "category": "Advantech",
        "description": "Affiche les informations sur le matériel"
    },
    {
        "text": "reset saved-configuration UID", "type": "NEXT", "category": "BLEU_SEED",
        "description": "Efface la configuration sauvegardée"
    },
    {
        "text": "sudo salt reset UID", "type": "all", "category": "BLEU_SEED",
        "description": "Réinitialise le service salt (à utiliser avec UID)"
    }
]

# --- Helper Functions ---
def get_category_name(category_code):
    name_map = {
        "G23": "G23",
        "Advantech": "Advantech",
        "BLEU_SEED": "BLEU/SEED"
    }
    return name_map.get(category_code, category_code)

def add_to_history(command_text):
    if command_text not in st.session_state.command_history:
        st.session_state.command_history.insert(0, command_text)
        if len(st.session_state.command_history) > 20:  # Limit history
            st.session_state.command_history.pop()

def show():
    st.title("Diagnostic Individuel")
    st.markdown("Entrez l'identifiant d'une gateway pour effectuer des opérations de diagnostic.")

    # --- Inputs ---
    col1, col2 = st.columns([2, 3])

    with col1:
        router_type_options = ["all", "OLD", "NEXT"]
        selected_router_type = st.selectbox(
            "Type d'équipement :",
            options=router_type_options,
            index=0,  # Default to 'all'
            key="router_type_filter"
        )

        uid_input = st.text_input(
            "Identifiant unique (UID) :",
            placeholder="ex : 1234-ABC",
            help="Format exemple: 1234-ABC (Sera automatiquement intégré aux commandes si 'UID' y est présent)"
        ).strip()

    # --- Display UID-Specific Commands ---
    st.markdown("---")  # Visual separator
    if uid_input:
        st.subheader("Commandes spécifiques à l'UID")
        commands_to_show = []
        if selected_router_type == "NEXT" or selected_router_type == "all":
            commands_to_show.append({
                "title": "Reset Gateway (NEXT GEN)",
                "cmd": f"sudo lwsalt reset '{uid_input}'"
            })
            commands_to_show.append({
                "title": "Vérifier Présence (NEXT GEN)",
                "cmd": f"sudo lwsalt list | grep {uid_input}"
            })
        if selected_router_type == "OLD" or selected_router_type == "all":
            commands_to_show.append({
                "title": "Reboot (OLD GEN)",
                "cmd": f"sudo salt '{uid_input}' cmd.run 'reboot'"
            })
            commands_to_show.append({
                "title": "Test Ping (OLD GEN)",
                "cmd": f"sudo salt {uid_input} test.ping"
            })

        if commands_to_show:
            uid_cols = st.columns(len(commands_to_show) if len(commands_to_show) <= 2 else 2)  # Max 2 side-by-side
            for i, cmd_info in enumerate(commands_to_show):
                with uid_cols[i % len(uid_cols)]:
                    st.markdown(f"<div class='uid-command-display'><strong>{cmd_info['title']}</strong>", unsafe_allow_html=True)
                    st.code(cmd_info['cmd'], language='bash')
                    st.markdown("</div>", unsafe_allow_html=True)
                    if st.button(f"Copier: {cmd_info['title']}", key=f"copy_uid_cmd_{i}"):
                        add_to_history(cmd_info['cmd'])
                        st.success(f"Commande '{cmd_info['title']}' prête à être copiée (via l'icône sur le bloc de code). Ajoutée à l'historique.")

        else:
            if selected_router_type not in ["OLD", "NEXT"]:  # e.g. if 'all' and no UID specific commands defined for 'all'
                st.info("Aucune commande spécifique à l'UID pour le type d'équipement 'all' (général). Les commandes spécifiques s'affichent si vous sélectionnez 'OLD' ou 'NEXT'.")
            else:
                st.info(f"Aucune commande spécifique à l'UID définie pour le type d'équipement '{selected_router_type}'.")

    st.markdown("---")  # Visual separator

    # --- Search and Tabs ---
    search_query = st.text_input(
        "🔍 Filtrer les commandes par mot-clé:",
        placeholder="Entrez un mot-clé pour filtrer les descriptions ou commandes..."
    ).lower()

    categories = ["all"] + sorted(list(set(cmd["category"] for cmd in commands_data)))
    tab_titles = [get_category_name(cat) if cat != "all" else "Toutes" for cat in categories]
    selected_tabs = st.tabs(tab_titles)

    # --- Display Filtered Commands ---
    for i, tab_name in enumerate(tab_titles):
        with selected_tabs[i]:
            current_tab_category = categories[i]

            st.subheader(f"Commandes: {tab_name}")

            filtered_commands_for_tab = []
            for cmd in commands_data:
                # Filter by router type
                type_match = (selected_router_type == "all" or
                              cmd["type"] == selected_router_type or
                              cmd["type"] == "all")

                # Filter by category for the current tab
                category_match = (current_tab_category == "all" or
                                  cmd["category"] == current_tab_category)

                # Filter by search query (in text or description)
                search_match = (not search_query or
                                search_query in cmd["text"].lower() or
                                search_query in cmd["description"].lower())

                if type_match and category_match and search_match:
                    final_cmd_text = cmd["text"]
                    if uid_input and "UID" in cmd["text"]:
                        final_cmd_text = cmd["text"].replace("UID", uid_input)
                    filtered_commands_for_tab.append({**cmd, "processed_text": final_cmd_text})

            if not filtered_commands_for_tab:
                st.info("Aucune commande ne correspond à vos critères de filtre dans cette catégorie.")
            else:
                for idx, command_item in enumerate(filtered_commands_for_tab):
                    with st.container():  # Use st.container for better grouping and styling
                        st.markdown(f"""
                        <div class='command-item-container'>
                            <span class='command-category-badge'>{get_category_name(command_item['category'])}</span>
                            <strong>{command_item['processed_text']}</strong>
                            <div class='command-desc'>{command_item['description']}</div>
                        </div>
                        """, unsafe_allow_html=True)

                        if st.button(f"Préparer & Ajouter à l'historique", key=f"cmd_{current_tab_category}_{idx}"):
                            add_to_history(command_item['processed_text'])
                            st.success(f"Commande '{command_item['description']}' ajoutée à l'historique. Copiez-la depuis le bloc ci-dessous.")

                        # Display in st.code for easy copying
                        st.code(command_item['processed_text'], language='bash')
                        st.markdown("---")