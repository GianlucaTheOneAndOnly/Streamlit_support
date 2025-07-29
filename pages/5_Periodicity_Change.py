import streamlit as st
import pandas as pd
import io
import pytz
from datetime import datetime, timedelta, time
from functools import wraps

# --- AUTHENTIFICATION (FONCTION FACTICE) ---
def secure_page(func):
    """Un décorateur factice pour représenter une page sécurisée."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

# --- FONCTIONS UTILITAIRES GLOBALES ---
@st.cache_data
def convert_df_to_csv(df):
    """Exporte un DataFrame en CSV sans en-têtes, encodé en UTF-8."""
    return df.to_csv(index=False, header=False, sep=',').encode('utf-8')

def safe_to_int(value):
    """Convertit une valeur en entier de manière sécurisée, en gérant les NaN."""
    if pd.isna(value):
        return ''
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return ''

def transform_data(hierarchy_data, tasks_data, periodicity_settings, interval_minutes, start_time, end_time, source_timezone_str, target_timezone_str):
    """
    Transforme les données en utilisant un fuseau horaire source pour la génération
    et un fuseau horaire cible pour la sortie.
    """
    debug_stats = {
        "hierarchy_assets": 0, "tasks_processed": 0, "assets_matched": 0,
        "skipped_by_until": 0, "skipped_by_params": 0, "final_rows": 0,
        "hierarchy_examples": [], "task_asset_examples": [], "params_examples": [],
    }
    hierarchy_list = [hierarchy_data.columns.values.tolist()] + hierarchy_data.values.tolist()
    tasks_list = [tasks_data.columns.values.tolist()] + tasks_data.values.tolist()

    source_tz = pytz.timezone(source_timezone_str)
    target_tz = pytz.timezone(target_timezone_str)

    try:
        hierarchy_headers = [str(h).strip() for h in hierarchy_list[0]]
        asset_column_index = hierarchy_headers.index('_id')
    except ValueError:
        st.error("FATAL: La colonne '_id' est introuvable dans le fichier Hierarchy. Veuillez vérifier le fichier.")
        return pd.DataFrame(), debug_stats

    hierarchy_lookup = { str(row[asset_column_index]): True for row in hierarchy_list[1:] if len(row) > asset_column_index and row[asset_column_index] }
    debug_stats["hierarchy_assets"] = len(hierarchy_lookup)
    debug_stats["hierarchy_examples"] = list(hierarchy_lookup.keys())[:5]
    tasks_headers = [str(header).strip() for header in tasks_list[0]]
    indices = {col: tasks_headers.index(col) for col in tasks_headers if col}

    headers = ['asset', 'presid', 'channel', 'unit', 'time_interval', 'fmin', 'fmax', 'task_type', 'time_acquisition']
    new_table = [headers]
    task_assets_seen = set()

    current_dt_aware = source_tz.localize(datetime.now())
    time_interval_decrement = timedelta(minutes=interval_minutes)
    
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

            task_type_value = str(row[indices.get('params[0]', -1)]) if 'params[0]' in indices else ''
            channel_raw = row[indices.get('params[8]', -1)] if 'params[8]' in indices else None
            
            try:
                channel_value = int(float(channel_raw))
            except (ValueError, TypeError):
                channel_value = None
            
            was_row_processed = False
            unit_value = ''
            time_interval_value = row[indices.get('rule.interval', -1)] if 'rule.interval' in indices else 1

            if task_type_value == 'acquire_dna':
                task_type_value = 'dna500;dna12;ave12'
                unit_value = periodicity_settings['dna']['freq']
                time_interval_value = periodicity_settings['dna']['interval']
                was_row_processed = True
            elif channel_value == 4 and task_type_value == 'acquire':
                task_type_value = '' 
                unit_value = periodicity_settings['temperature']['freq']
                time_interval_value = periodicity_settings['temperature']['interval']
                was_row_processed = True
            elif channel_value in [0, 1, 2, 3] and task_type_value == 'acquire':
                task_type_value = 'velocity;acceleration'
                unit_value = periodicity_settings['velocity']['freq']
                time_interval_value = periodicity_settings['velocity']['interval']
                was_row_processed = True
            
            if was_row_processed:
                current_time = current_dt_aware.time()
                if current_time > end_time:
                    naive_dt = datetime.combine(current_dt_aware.date(), end_time)
                    current_dt_aware = source_tz.localize(naive_dt)
                elif current_time < start_time:
                    naive_dt = datetime.combine(current_dt_aware.date() - timedelta(days=1), end_time)
                    current_dt_aware = source_tz.localize(naive_dt)

                target_dt = current_dt_aware.astimezone(target_tz)
                time_acquisition_value = target_dt.strftime('%Y-%m-%d %H:%M')
                
                row_data = [ mongo_asset, row[indices.get('presid', -1)] if 'presid' in indices else '', channel_value, unit_value, time_interval_value, safe_to_int(row[indices.get('statistics.vibration[0].fmin')]), safe_to_int(row[indices.get('statistics.vibration[0].fmax')]), task_type_value, time_acquisition_value ]
                new_table.append(row_data)
                
                current_dt_aware -= time_interval_decrement
            else:
                debug_stats["skipped_by_params"] += 1
                if len(debug_stats["params_examples"]) < 5:
                    example = f"asset: {mongo_asset}, task_type (params[0]): '{task_type_value}', channel (params[8]): '{channel_raw}'"
                    debug_stats["params_examples"].append(example)

    debug_stats["task_asset_examples"] = list(task_assets_seen)
    if len(new_table) > 1:
        df = pd.DataFrame(new_table[1:], columns=new_table[0])
        debug_stats["final_rows"] = len(df)
        return df, debug_stats
    else:
        return pd.DataFrame(), debug_stats

# --- FONCTION PRINCIPALE DE LA PAGE ---
@secure_page
def render_csv_processor_page():
    st.title("⚙️ CSV Processing Tool")

    if 'processed_data' not in st.session_state:
        st.session_state.processed_data = None

    # Section 1: Réglages
    st.header("1. Define Settings")

    # --- Timezone Selectors ---
    st.subheader("🌍 Timezone Settings")
    timezones = [
        "Europe/Brussels", "UTC", "Europe/London", "America/New_York", 
        "America/Chicago", "America/Denver", "America/Los_Angeles", "Asia/Tokyo", "Asia/Dubai", "Asia/Kolkata", "Australia/Sydney"
    ]
    tz_col1, tz_col2 = st.columns(2)
    with tz_col1:
        source_timezone = st.selectbox("My Timezone (Source)", options=timezones, index=0, help="Le fuseau horaire de votre emplacement actuel. Utilisé pour interpréter `maintenant`.")
    with tz_col2:
        target_timezone = st.selectbox("Target Timezone (Output)", options=timezones, index=0, help="Le fuseau horaire final pour la colonne `time_acquisition`.")
    
    st.markdown("---")
    
    col_period, col_interval = st.columns([3, 1])
    with col_period:
        st.subheader("Measurement Frequencies")
        p1, p2, p3 = st.columns(3)
        with p1:
            velocity_period = st.selectbox("Velocity", options=['DAILY', 'WEEKLY', 'MONTHLY', 'HOURLY', 'MINUTELY'], index=3, key="v_freq")
            velocity_interval = st.number_input("Velocity Interval", min_value=1, value=24, step=1, key="v_int")
        with p2:
            dna_period = st.selectbox("DNA", options=['DAILY', 'WEEKLY', 'MONTHLY', 'HOURLY', 'MINUTELY'], index=3, key="d_freq")
            dna_interval = st.number_input("DNA Interval", min_value=1, value=24, step=1, key="d_int")
        with p3:
            temp_period = st.selectbox("Temperature", options=['DAILY', 'WEEKLY', 'MONTHLY', 'HOURLY', 'MINUTELY'], index=3, key="t_freq")
            temp_interval = st.number_input("Temp. Interval", min_value=1, value=24, step=1, key="t_int")

    with col_interval:
        st.subheader("Time Interval")
        time_interval_minutes = st.number_input("Interval between tasks (minutes)", min_value=1, value=19, step=1)
        
        st.subheader("Time Window Filter")
        start_time = st.time_input("Start of day", value=time(0, 0), help="Heure de début pour l'acquisition des tâches.")
        end_time = st.time_input("End of day", value=time(23, 59), help="Heure de fin pour l'acquisition des tâches.")

    if (end_time.hour - start_time.hour) < 23:
        st.info("ℹ️ **Recommandation :** Puisque vous utilisez une fenêtre de temps restreinte, il est recommandé de régler la fréquence des mesures sur 'DAILY' (ou un intervalle de 24 heures).")

    periodicity_settings = { "velocity": {"freq": velocity_period, "interval": velocity_interval}, "dna": {"freq": dna_period, "interval": dna_interval}, "temperature": {"freq": temp_period, "interval": temp_interval} }

    st.markdown("---")

    # Section 2: Upload des fichiers
    st.header("2. Upload Files")
    col1_upload, col2_upload = st.columns(2)
    with col1_upload:
        hierarchy_file = st.file_uploader("Choose the Hierarchy file", type=['csv'])
        st.info("ℹ️ Ce fichier peut être généré via la page **4_Download_Hierarchy**.")
    with col2_upload:
        tasks_file = st.file_uploader("Choose the Tasks file", type=['csv'])
        st.info("ℹ️ Ce fichier est obtenu via un export de la base de données **MongoDB**.")

    # Section 3: Traitement et Diagnostics
    if hierarchy_file is not None and tasks_file is not None:
        st.header("3. Start Processing")
        
        if st.button("Process Files", type="primary"):
            with st.spinner('Processing...'):
                hierarchy_df = pd.read_csv(hierarchy_file)
                tasks_df = pd.read_csv(tasks_file)
                
                transformed_df, debug_stats = transform_data( hierarchy_df, tasks_df, periodicity_settings, time_interval_minutes, start_time, end_time, source_timezone, target_timezone )

                st.subheader("🔍 Diagnostic Results")
                st.info(f"**Unique assets found in `Hierarchy`:** {debug_stats['hierarchy_assets']}")
                st.info(f"**Total rows processed from `Tasks`:** {debug_stats['tasks_processed']}")
                st.info(f"**Asset matches found:** {debug_stats['assets_matched']}")
                st.warning(f"**Rows skipped due to 'rule.until':** {debug_stats['skipped_by_until']}")
                st.warning(f"**Rows skipped (unrecognized parameters):** {debug_stats['skipped_by_params']}")
                
                if debug_stats["params_examples"]:
                    st.info("Examples of rows with unrecognized parameters:")
                    for example in debug_stats["params_examples"]:
                        st.code(example, language='text')
                st.success(f"**Final rows generated:** {debug_stats['final_rows']}")

                if debug_stats['final_rows'] == 0 and debug_stats['assets_matched'] > 0:
                    st.error("❌ **PROBLÈME IDENTIFIÉ :** Aucune ligne n'a été générée. Vérifiez les compteurs ci-dessus.")

                st.session_state.processed_data = transformed_df if not transformed_df.empty else None

    # Section 4: Téléchargement du résultat
    if st.session_state.get('processed_data') is not None and not st.session_state.processed_data.empty:
        st.markdown("---")
        st.header("4. Download Result")
        st.dataframe(st.session_state.processed_data)
        
        csv_data = convert_df_to_csv(st.session_state.processed_data)
        
        st.download_button( label="📥 Download CSV file", data=csv_data, file_name='tasks.csv', mime='text/csv', )

# --- APPEL POUR AFFICHER LA PAGE ---
render_csv_processor_page()