import streamlit as st
import pandas as pd
from io import StringIO
from src.auth import secure_page



@secure_page
def render_firmware_update():

    """Generate CSV file for firmwares updates"""

    st.title("🗂️ Firmware update CSV file")
    st.markdown("---")

    st.markdown("""
    This tool allows you to generate a CSV file with the proper formatting.
    - **Colonne 1** : I-see URL ID (one each line)
    - **Colonne 4** : Firmware version
    - **Colonnes 2 et 3** : empty
    """)

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("📝 I-see URL ID list")
        input_data = st.text_area(
            "Enter URL ID (un par ligne):",
            height=300,
            placeholder="Exemple:\n640835b17df06ddd1123b5f8\n640835b17df06ddd1123b5f9",
            help="Add only one url per line"
        )

    with col2:
        st.subheader("⚙️ Configuration")
        command_options = [
            "Gateway",
            "Transmitter",
        ]
        
        selected_command = st.selectbox(
            "Select the component type to update :",
            options=command_options,
            index=0
        )
        
        # Set firmware version based on selection
        if selected_command == "Gateway":
            firmware_version = "00010405"
            help_text = "Firmware version (by default: 00010405)"
        elif selected_command == "Transmitter":
            firmware_version = "170001d"
            help_text = "Firmware version (by défaut: 170001d)"
        
        st.info(f"Selected firmware version: **{firmware_version}**")
        
        with st.expander("Advanced options"):
            remove_empty_lines = st.checkbox("Remove empty lines", value=True)
            filename = st.text_input("File name:", value="gw_firm.csv")

    if input_data:
        id_list = input_data.strip().split('\n')
        
        if remove_empty_lines:
            id_list = [id_.strip() for id_ in id_list if id_.strip()]
        
        st.info(f"📊 **{len(id_list)}** identifier(s) found")
        
        if id_list:
            # Ensure firmware version is treated as string with leading zeros preserved
            df_data = [[id_, "", "", firmware_version] for id_ in id_list]
            df = pd.DataFrame(df_data, columns=["Identifier", "Column2", "Column", "Firmware_version"])
            
            # Explicitly set the firmware version column as string type
            df = pd.DataFrame(df_data, columns=["Identifier", "Column2", "Column", "Firmware_version"])
            df['Firmware_version'] = df['Firmware_version'].astype(str)
            
            with st.expander("🔍 Preview CSV file", expanded=True):
                st.dataframe(df, use_container_width=True)
                
                st.subheader("Preview CSV file (no headers):")
                csv_content = df.to_csv(index=False, header=False)
                st.code(csv_content, language="csv")
            
            st.markdown("---")
            col_gen1, col_gen2 = st.columns([1, 1])
            
            with col_gen1:
                if st.button("🚀 Generate CSV", type="primary", use_container_width=True):
                    # Generate CSV as Google Sheets would - with proper quoting for leading zeros
                    csv_lines = []
                    for _, row in df.iterrows():
                        csv_line = f'{row["Identifier"]},,,{firmware_version}'
                        csv_lines.append(csv_line)
                    csv_content = '\n'.join(csv_lines) + '\n'
                                        
                    st.success("✅ CSV successfully generated !")
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
                    csv_line = f'{row["Identifier"]},,,{firmware_version}'
                    csv_lines.append(csv_line)
                csv_for_download = '\n'.join(csv_lines) + '\n'
                
                st.download_button(
                    label="💾 Download CSV",
                    data=csv_for_download,
                    file_name=filename,
                    mime="text/csv",
                    use_container_width=True
                )

    else:
        st.info("👆 Please enter at least one I-see URL ID to generate CSV.")

    st.markdown("---")
    st.subheader("📜 Files generation history")

    if 'csv_history' not in st.session_state:
        st.session_state.csv_history = []

    if not st.session_state.csv_history:
        st.write("No file generated yet.")
    else:
        for i, history_item in enumerate(reversed(st.session_state.csv_history)):
            with st.expander(f"📄 {history_item['filename']} - {history_item['count']} Identifier(s)"):
                col_hist1, col_hist2 = st.columns([2, 1])
                
                with col_hist1:
                    st.write(f"**Identifiers :** {history_item['count']}")
                    st.write(f"**Version firmware :** {history_item['firmware_version']}")
                    st.code(history_item['content'][:200] + "..." if len(history_item['content']) > 200 else history_item['content'], language="csv")
                
                with col_hist2:
                    st.download_button(
                        label="💾 Download again",
                        data=history_item['content'],
                        file_name=history_item['filename'],
                        mime="text/csv",
                        key=f"redownload_{i}"
                    )

    if st.session_state.csv_history:
        if st.button("🗑️ Delete CSV history"):
            st.session_state.csv_history = []
            st.rerun()

render_firmware_update()