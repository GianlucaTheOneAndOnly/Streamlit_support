import streamlit as st
import pandas as pd
import io
from datetime import datetime, timedelta
from functools import wraps  # Make sure to import wraps if needed for your decorator
from src.auth import secure_page

# --- GLOBALLY DEFINED UTILITY FUNCTIONS ---

@st.cache_data
def convert_df_to_csv(df):
    """Exports a DataFrame to CSV without headers, encoded in UTF-8."""
    return df.to_csv(index=False, header=False, sep=',').encode('utf-8')

def safe_to_int(value):
    """Safely converts a value to an integer, handling NaN values."""
    if pd.isna(value):
        return ''
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return ''

def transform_data(hierarchy_data, tasks_data, periodicity_settings, interval_minutes):
    """
    Transforms data based on user settings and returns a DataFrame
    and debugging statistics.
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
    new_table = [headers]
    task_assets_seen = set()

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
                dtstart_value = current_dtstart.strftime('%d/%m/%Y %H:%M')
                
                row_data = [
                    mongo_asset,
                    row[indices.get('presid', -1)] if 'presid' in indices else '',
                    params8_value, rule_freq_value, rule_interval_value,
                    safe_to_int(row[indices.get('statistics.vibration[0].fmin')]),
                    safe_to_int(row[indices.get('statistics.vibration[0].fmax')]),
                    params0_value, dtstart_value
                ]
                new_table.append(row_data)

                current_dtstart += time_interval
            else:
                debug_stats["skipped_by_params"] += 1
                if len(debug_stats["params_examples"]) < 5:
                    example = f"asset: {mongo_asset}, params[0]: '{params0_value}', params[8]: '{params8_raw}'"
                    debug_stats["params_examples"].append(example)

    debug_stats["task_asset_examples"] = list(task_assets_seen)
    if len(new_table) > 1:
        df = pd.DataFrame(new_table[1:], columns=new_table[0])
        debug_stats["final_rows"] = len(df)
        return df, debug_stats
    else:
        return pd.DataFrame(), debug_stats

# --- MAIN PAGE FUNCTION WITH DECORATOR ---
@secure_page
def render_csv_processor_page():
    st.title("⚙️ CSV Processing Tool")

    if 'processed_data' not in st.session_state:
        st.session_state.processed_data = None

    # Section 1: Settings
    st.header("1. Define Settings")
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

    periodicity_settings = {
        "velocity": {"freq": velocity_period, "interval": velocity_interval},
        "dna": {"freq": dna_period, "interval": dna_interval},
        "temperature": {"freq": temp_period, "interval": temp_interval}
    }

    st.markdown("---")

    # Section 2: File Upload
    st.header("2. Upload Files")
    col1_upload, col2_upload = st.columns(2)
    with col1_upload:
        hierarchy_file = st.file_uploader("Choose the Hierarchy file", type=['csv'])
        st.info("ℹ️ This file can be generated via the **4_Download_Hierarchy** page.")
    with col2_upload:
        tasks_file = st.file_uploader("Choose the Tasks file", type=['csv'])
        st.info("ℹ️ This file is obtained via an export from the **MongoDB** database.")

    # Section 3: Processing and Diagnostics
    if hierarchy_file is not None and tasks_file is not None:
        st.header("3. Start Processing")
        
        if st.button("Process Files", type="primary"):
            with st.spinner('Processing...'):
                hierarchy_df = pd.read_csv(hierarchy_file)
                tasks_df = pd.read_csv(tasks_file)
                
                transformed_df, debug_stats = transform_data(hierarchy_df, tasks_df, periodicity_settings, time_interval_minutes)

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
                    st.error("❌ **PROBLEM IDENTIFIED:** No rows were generated. Check the counters above.")

                st.session_state.processed_data = transformed_df if not transformed_df.empty else None

    # Section 4: Download Result
    if st.session_state.get('processed_data') is not None and not st.session_state.processed_data.empty:
        st.markdown("---")
        st.header("4. Download Result")
        st.dataframe(st.session_state.processed_data)
        
        # Call the `convert_df_to_csv` function which was defined globally
        csv_data = convert_df_to_csv(st.session_state.processed_data)
        
        st.download_button(
            label="📥 Download CSV file",
            data=csv_data,
            file_name='transformed_data.csv',
            mime='text/csv',
        )

# --- CALL TO DISPLAY THE PAGE ---
render_csv_processor_page()