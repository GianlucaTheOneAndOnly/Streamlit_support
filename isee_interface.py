# isee_interface.py

import streamlit as st
from iseeapi_streamlite import Api # Import the Api class from the other file

# It's good practice to import libraries you use directly, even if they are used
# by the imported class. Here, we need pandas for the .to_csv() method.
import pandas as pd

# --- Page and State Configuration ---
st.set_page_config(layout="wide", page_title="I-CARE Data Extractor")

# Initialize all session state keys we will use
if 'api_client' not in st.session_state:
    st.session_state.api_client = None
if 'db_list' not in st.session_state:
    st.session_state.db_list = None
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'hierarchy_df' not in st.session_state:
    st.session_state.hierarchy_df = None
if 'listname_df' not in st.session_state:
    st.session_state.listname_df = None


# --- UI Rendering ---

st.title("I-CARE API Data Extractor")

# --- Login UI (in the sidebar) ---
with st.sidebar:
    st.header("Login Credentials")
    
    # Disable inputs if already logged in
    is_disabled = st.session_state.logged_in
    
    username = st.text_input("Username", disabled=is_disabled)
    password = st.text_input("Password", type="password", disabled=is_disabled)
    server = st.selectbox("Select Server", Api.SERVER_RESPONSE, disabled=is_disabled)

    if st.button("Login", disabled=is_disabled):
        if username and password:
            with st.spinner("Logging in..."):
                # Instantiate the API class from our other file
                api = Api(username, password)
                db_result = api.login_step1_get_dbs(server)

                if isinstance(db_result, list): # Success
                    st.session_state.api_client = api
                    st.session_state.db_list = db_result
                    st.success("Login successful! Please select a database.")
                else: # Error message string was returned
                    st.error(db_result)
        else:
            st.warning("Please enter both username and password.")

    # --- Database Selection UI (also in sidebar) ---
    if st.session_state.db_list and not st.session_state.logged_in:
        db_options = {db['name']: db['db'] for db in st.session_state.db_list}
        selected_db_name = st.selectbox(
            "Select Database",
            options=db_options.keys(),
            index=None,
            placeholder="Choose a database..."
        )

        if selected_db_name and st.button("Confirm Database"):
            selected_db_id = db_options[selected_db_name]
            with st.spinner("Accessing database..."):
                api_client = st.session_state.api_client
                result = api_client.login_step2_select_db(selected_db_id)

                if result is True:
                    st.session_state.logged_in = True
                    st.session_state.api_client = api_client
                    st.success(f"Connected to: {selected_db_name}")
                    st.rerun() # Rerun to update the main page view
                else: # Error message string was returned
                    st.error(result)

# --- Main App Content Area ---
if not st.session_state.logged_in:
    st.info("Please log in using the sidebar to begin.")
else:
    st.header("Hierarchy Extraction")
    if st.button("Fetch Asset Hierarchy", type="primary"):
        # Clear previous results before fetching new ones
        st.session_state.hierarchy_df = None
        st.session_state.listname_df = None
        
        api_client = st.session_state.api_client
        h_df, l_df = api_client.get_hierarchy()

        if h_df is not None and l_df is not None:
            st.session_state.hierarchy_df = h_df
            st.session_state.listname_df = l_df
            st.success("Data extraction and processing complete!")
        else:
            st.error("Failed to extract data. Check the logs above for details.")

    # --- Display DataFrames and Download Buttons ---
    if st.session_state.hierarchy_df is not None:
        st.subheader("Processed Hierarchy Data")
        st.dataframe(st.session_state.hierarchy_df)
        st.download_button(
            label="Download Hierarchy as CSV",
            data=st.session_state.hierarchy_df.to_csv(index=False).encode('utf-8'),
            file_name='hierarchy_data.csv',
            mime='text/csv',
        )

    if st.session_state.listname_df is not None:
        st.subheader("Asset List Data")
        st.dataframe(st.session_state.listname_df)
        st.download_button(
            label="Download Asset List as CSV",
            data=st.session_state.listname_df.to_csv(index=False).encode('utf-8'),
            file_name='listname_data.csv',
            mime='text/csv',
        )