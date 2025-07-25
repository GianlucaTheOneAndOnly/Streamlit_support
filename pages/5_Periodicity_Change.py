import streamlit as st
import pandas as pd
import io
from datetime import datetime, timedelta
from src.auth import secure_page  # Import your decorator

# Helper function to prevent conversion errors
def safe_to_int(value):
    """Safely converts a value to an integer, handling NaN and other errors."""
    if pd.isna(value):
        return ''
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return ''

def transformer_donnees(hierarchy_data, tasks_data, periodicity_settings, interval_minutes):
    """
    Transforms data based on user settings and returns a DataFrame and debug statistics.
    """
    debug_stats = {
        "hierarchy_assets": 0, "tasks_processed": 0, "assets_matched": 0,
        "skipped_by_until": 0, "skipped_by_params": 0, "final_rows": 0,
        "hierarchy_examples": [], "task_asset_examples": [], "params_examples": [],
    }
    hierarchy_list = [hierarchy_data.columns.values.tolist()] + hierarchy_data.values.tolist()
    tasks_list = [tasks_data.columns.values.tolist()] + tasks_data.values.tolist()
    hierarchy_lookup = {str(row[13]): True for row in hierarchy_list[1:] if len(row) > 13 and row[13]}
    debug_stats["hierarchy_assets"] = len(hierarchy_lookup)
    debug_stats["hierarchy_examples"] = list(hierarchy_lookup.keys())[:5]
    tasks_headers = [str(header).strip() for header in tasks_list[0]]
    indices = {col: tasks_headers.index(col) for col in tasks_headers if col}
    headers = ['asset', 'presid', 'params8', 'rule.freq', 'rule.interval', 
               'statistics.vibration[0].fmin', 'statistics.vibration[0].fmax', 'params0', 'rule.dtstart']
    nouvelle_table = [headers]
    task_assets_seen = set()

    # --- CHANGE 1: Initialize start time and interval ---
    current_dtstart = datetime.now()
    time_interval = timedelta(minutes=interval_minutes)
    
    for row in tasks_list[1:]:
        debug_stats["tasks_processed"] += 1
        
        try:
            mongo_asset = str(row[indices['asset']])
            if len(task_assets_seen) < 5:
                task_assets_seen.add(mongo_asset)
        except (IndexError, KeyError):
            continue

        if mongo_asset in hierarchy_lookup:
            debug_stats["assets_matched"] += 1
            
            rule_until_value = str(row[indices.get('rule.until', -1)]).strip() if 'rule.until' in indices else ''
            if rule_until_value and rule_until_value.lower() not in ['nan', '']:
                debug_stats["skipped_by_until"] += 1
                continue

            params0_value = str(row[indices.get('params[0]', -1)]) if 'params[0]' in indices else ''
            params8_raw = row[indices.get('params[8]', -1)] if 'params[8]' in indices else None
            params8_value = int(params8_raw) if str(params8_raw).isdigit() else None
            
            was_row_processed = False
            rule_freq_value = ''
            rule_interval_value = row[indices.get('rule.interval', -1)] if 'rule.interval' in indices else 1

            if params0_value == 'acquire_dna':
                params0_value = 'dna500;dna12;ave12'
                rule_freq_value = periodicity_settings['dna']['freq']
                rule_interval_value = periodicity_settings['dna']['interval']
                was_row_processed = True
            elif params8_value == 4 and params0_value == 'acquire':
                params0_value = ''
                rule_freq_value = periodicity_settings['temperature']['freq']
                rule_interval_value = periodicity_settings['temperature']['interval']
                was_row_processed = True
            elif params8_value in [0, 1, 2, 3] and params0_value == 'acquire':
                params0_value = 'velocity;acceleration'
                rule_freq_value = periodicity_settings['velocity']['freq']
                rule_interval_value = periodicity_settings['velocity']['interval']
                was_row_processed = True
            
            if was_row_processed:
                # --- CHANGE 2: Generate dtstart value based on current time and interval ---
                dtstart_value = current_dtstart.strftime('%d/%m/%Y %H:%M')
                
                row_data = [
                    mongo_asset,
                    row[indices.get('presid', -1)] if 'presid' in indices else '',
                    params8_value, rule_freq_value, rule_interval_value,
                    safe_to_int(row[indices.get('statistics.vibration[0].fmin')]),
                    safe_to_int(row[indices.get('statistics.vibration[0].fmax')]),
                    params0_value, dtstart_value
                ]
                nouvelle_table.append(row_data)

                # Increment the time for the next valid row
                current_dtstart += time_interval
            else:
                debug_stats["skipped_by_params"] += 1
                if len(debug_stats["params_examples"]) < 5:
                    example = f"asset: {mongo_asset}, params[0]: '{params0_value}', params[8]: '{params8_raw}'"
                    debug_stats["params_examples"].append(example)

    debug_stats["task_asset_examples"] = list(task_assets_seen)
    if len(nouvelle_table) > 1:
        df = pd.DataFrame(nouvelle_table[1:], columns=nouvelle_table[0])
        debug_stats["final_rows"] = len(df)
        return df, debug_stats
    else:
        return pd.DataFrame(), debug_stats

# --- Main Page Function with Decorator ---
@secure_page
def render_csv_processor_page():
    # --- Streamlit Page UI ---
    st.set_page_config(page_title="CSV Processor", layout="wide")
    st.title("⚙️ Outil de Traitement CSV")

    # --- Main content: Only show if logged in and database is selected ---
    if st.session_state.get('logged_in'):
        st.markdown("---")

        # Section 1: Periodicity and Interval Settings
        st.header("1. Définir les Paramètres")
        col_period, col_interval = st.columns([3, 1])

        with col_period:
            st.subheader("Périodicités de mesure")
            p1, p2, p3 = st.columns(3)
            with p1:
                velocity_period = st.selectbox("Vélocité", options=['DAILY', 'WEEKLY', 'MONTHLY', 'HOURLY', 'MINUTELY'], index=0, key="v_freq")
                velocity_interval = st.number_input("Intervalle Vélocité", min_value=1, value=1, step=1, key="v_int")
            with p2:
                dna_period = st.selectbox("DNA", options=['DAILY', 'WEEKLY', 'MONTHLY', 'HOURLY', 'MINUTELY'], index=1, key="d_freq")
                dna_interval = st.number_input("Intervalle DNA", min_value=1, value=1, step=1, key="d_int")
            with p3:
                temp_period = st.selectbox("Température", options=['DAILY', 'WEEKLY', 'MONTHLY', 'HOURLY', 'MINUTELY'], index=2, key="t_freq")
                temp_interval = st.number_input("Intervalle Temp.", min_value=1, value=1, step=1, key="t_int")

        with col_interval:
            st.subheader("Intervalle Temporel")
            # --- CHANGE 3: Add UI for time interval ---
            time_interval_minutes = st.number_input("Intervalle entre tâches (minutes)", min_value=1, value=19, step=1)

        periodicity_settings = {
            "velocity": {"freq": velocity_period, "interval": velocity_interval},
            "dna": {"freq": dna_period, "interval": dna_interval},
            "temperature": {"freq": temp_period, "interval": temp_interval}
        }

        st.markdown("---")

        # Section 2: File Uploads
        st.header("2. Télécharger les fichiers")
        col1_upload, col2_upload = st.columns(2)
        with col1_upload:
            hierarchy_file = st.file_uploader("Choisissez le fichier Hierarchy", type=['csv'])
            st.info("ℹ️ Ce fichier peut être généré via la page **4_Download_Hierarchy**.")
        with col2_upload:
            tasks_file = st.file_uploader("Choisissez le fichier Tasks", type=['csv'])
            st.info("ℹ️ Ce fichier est obtenu via une exportation depuis la base de données **MongoDB**.")

        # Section 3: Processing and Diagnostics
        if hierarchy_file is not None and tasks_file is not None:
            st.header("3. Lancer le traitement")
            
            if st.button("Traiter les fichiers", type="primary"):
                with st.spinner('Traitement en cours...'):
                    hierarchy_df = pd.read_csv(hierarchy_file)
                    tasks_df = pd.read_csv(tasks_file)
                    
                    # Pass the new time interval to the function
                    transformed_df, debug_stats = transformer_donnees(hierarchy_df, tasks_df, periodicity_settings, time_interval_minutes)

                    st.subheader("🔍 Résultats du diagnostic")
                    st.info(f"**Assets uniques trouvés dans `Hierarchy`:** {debug_stats['hierarchy_assets']}")
                    st.info(f"**Lignes totales traitées depuis `Tasks`:** {debug_stats['tasks_processed']}")
                    st.info(f"**Correspondances d'assets trouvées:** {debug_stats['assets_matched']}")
                    st.warning(f"**Lignes ignorées à cause de 'rule.until':** {debug_stats['skipped_by_until']}")
                    st.warning(f"**Lignes ignorées (paramètres non reconnus):** {debug_stats['skipped_by_params']}")
                    if debug_stats["params_examples"]:
                        st.info("Exemples de lignes avec des paramètres non reconnus :")
                        for example in debug_stats["params_examples"]:
                            st.code(example, language='text')
                    st.success(f"**Lignes finales générées:** {debug_stats['final_rows']}")

                    if debug_stats['final_rows'] == 0 and debug_stats['assets_matched'] > 0:
                         st.error("❌ **PROBLÈME IDENTIFIÉ:** Aucune ligne n'a été générée. Vérifiez les compteurs 'lignes ignorées' ci-dessus pour comprendre pourquoi.")

                    if not transformed_df.empty:
                        st.session_state.processed_data = transformed_df
                    else:
                        st.session_state.processed_data = None

        # Section 4: Download Result
        if st.session_state.get('processed_data') is not None and not st.session_state.processed_data.empty:
            st.markdown("---")
            st.header("4. Télécharger le résultat")
            st.dataframe(st.session_state.processed_data) # Display with headers in the app
            
            @st.cache_data
            def convert_df_to_csv(df):
                # --- CHANGE 4: Export without headers ---
                return df.to_csv(index=False, header=False, sep=',').encode('utf-8')

            csv_data = convert_df_to_csv(st.session_state.processed_data)
            
            st.download_button(
                label="📥 Télécharger le fichier CSV",
                data=csv_data,
                file_name='transformed_data.csv',
                mime='text/csv',
            )

# --- Call the main function to render the page ---
render_csv_processor_page()