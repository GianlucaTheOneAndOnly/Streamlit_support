import streamlit as st
import pandas as pd
from io import StringIO

def show():
    """Page pour générer des fichiers CSV avec des identifiants et une version firmware"""
    
    st.title("🗂️ Générateur de Fichier CSV")
    st.markdown("---")
    
    st.markdown("""
    Cet outil vous permet de générer un fichier CSV à partir d'une liste d'identifiants et d'une version firmware.
    - **Colonne 1** : Identifiants (un par ligne)
    - **Colonne 4** : Version firmware
    - **Colonnes 2 et 3** : Vides
    """)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📝 Liste des identifiants")
        input_data = st.text_area(
            "Entrez les identifiants (un par ligne):",
            height=300,
            placeholder="Exemple:\n640835b17df06ddd1123b5f8\n640835b17df06ddd1123b5f9",
            help="Ajoutez chaque identifiant sur une nouvelle ligne"
        )
    
    with col2:
        st.subheader("⚙️ Configuration")
        command_options = [
            "Gateway",
            "Transmitter",
        ]
        
        selected_command = st.selectbox(
            "Sélectionnez une commande à exécuter pour tous les gateways:",
            options=command_options,
            index=0
        )
        
        # Set firmware version based on selection
        if selected_command == "Gateway":
            firmware_version = "00010405"
            help_text = "Version firmware à appliquer (par défaut: 00010405)"
        elif selected_command == "Transmitter":
            firmware_version = "170001d"
            help_text = "Version firmware à appliquer (par défaut: 170001d)"
        
        st.info(f"Version firmware sélectionnée: **{firmware_version}**")
        
        with st.expander("Options avancées"):
            remove_empty_lines = st.checkbox("Supprimer les lignes vides", value=True)
            filename = st.text_input("Nom du fichier:", value="gw_firm.csv")
    
    if input_data:
        id_list = input_data.strip().split('\n')
        
        if remove_empty_lines:
            id_list = [id_.strip() for id_ in id_list if id_.strip()]
        
        st.info(f"📊 **{len(id_list)}** identifiant(s) trouvé(s)")
        
        if id_list:
            # Ensure firmware version is treated as string with leading zeros preserved
            df_data = [[id_, "", "", firmware_version] for id_ in id_list]
            df = pd.DataFrame(df_data, columns=["Identifiant", "Colonne2", "Colonne3", "Version_Firmware"])
            
            # Explicitly set the firmware version column as string type
            df['Version_Firmware'] = df['Version_Firmware'].astype(str)
            
            with st.expander("🔍 Aperçu du fichier CSV", expanded=True):
                st.dataframe(df, use_container_width=True)
                
                st.subheader("Aperçu CSV brut (sans headers):")
                csv_content = df.to_csv(index=False, header=False)
                st.code(csv_content, language="csv")
            
            st.markdown("---")
            col_gen1, col_gen2 = st.columns([1, 1])
            
            with col_gen1:
                if st.button("🚀 Générer le fichier CSV", type="primary", use_container_width=True):
                    # Generate CSV as Google Sheets would - with proper quoting for leading zeros
                    csv_lines = []
                    for _, row in df.iterrows():
                        csv_line = f'{row["Identifiant"]},,,{firmware_version}'
                        csv_lines.append(csv_line)
                    csv_content = '\n'.join(csv_lines) + '\n'
                                        
                    st.success("✅ Fichier CSV généré avec succès!")
                    st.balloons()
                    
                    if 'csv_history' not in st.session_state:
                        st.session_state.csv_history = []
                    
                    st.session_state.csv_history.append({
                        'filename': filename,
                        'count': len(id_list),
                        'firmware_version': firmware_version,
                        'content': csv_content
                    })
            
            with col_gen2:
                # Generate CSV as Google Sheets would - with proper quoting for leading zeros
                csv_lines = []
                for _, row in df.iterrows():
                    csv_line = f'{row["Identifiant"]},,,{firmware_version}'
                    csv_lines.append(csv_line)
                csv_for_download = '\n'.join(csv_lines) + '\n'
                
                st.download_button(
                    label="💾 Télécharger le CSV",
                    data=csv_for_download,
                    file_name=filename,
                    mime="text/csv",
                    use_container_width=True
                )
    
    else:
        st.info("👆 Veuillez entrer au moins un identifiant pour générer le fichier CSV.")
    
    st.markdown("---")
    st.subheader("📜 Historique des fichiers générés")
    
    if 'csv_history' not in st.session_state:
        st.session_state.csv_history = []
    
    if not st.session_state.csv_history:
        st.write("Aucun fichier généré pour le moment.")
    else:
        for i, history_item in enumerate(reversed(st.session_state.csv_history)):
            with st.expander(f"📄 {history_item['filename']} - {history_item['count']} identifiant(s)"):
                col_hist1, col_hist2 = st.columns([2, 1])
                
                with col_hist1:
                    st.write(f"**Identifiants :** {history_item['count']}")
                    st.write(f"**Version firmware :** {history_item['firmware_version']}")
                    st.code(history_item['content'][:200] + "..." if len(history_item['content']) > 200 else history_item['content'], language="csv")
                
                with col_hist2:
                    st.download_button(
                        label="💾 Re-télécharger",
                        data=history_item['content'],
                        file_name=history_item['filename'],
                        mime="text/csv",
                        key=f"redownload_{i}"
                    )
    
    if st.session_state.csv_history:
        if st.button("🗑️ Effacer l'historique CSV"):
            st.session_state.csv_history = []
            st.rerun()