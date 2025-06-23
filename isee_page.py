import streamlit as st
import pandas as pd
from iseeapi_streamlit import Api  # Assumes iseeapi_streamlit.py is in the same directory
import os

# --- Helper function to convert DataFrame to CSV for downloading ---
@st.cache_data
def convert_df_to_csv(df):
    """Converts a DataFrame to a CSV string for downloading."""
    return df.to_csv(index=False).encode('utf-8')

def show():
    """
    This function contains the Streamlit UI and logic for the iSee Data Extractor page.
    """
    st.header("iSee API Data Extractor")
    st.markdown("This section allows you to connect to the iSee API, fetch the asset hierarchy, and download the data as CSV files.")

    # --- Initialize API Class ---
    # This will use st.session_state to keep track of the login status and session object.
    api = Api()

    # --- Login and Controls (Can be in main content or a dedicated sidebar for this page) ---
    st.subheader("Login Credentials")
    
    # Check for credentials in st.secrets, otherwise provide text inputs
    try:
        default_username = st.secrets["credentials"]["username"]
        default_password = st.secrets["credentials"]["password"]
    except (FileNotFoundError, KeyError):
        default_username = ""
        default_password = ""

    username = st.text_input("Username", value=default_username, key="isee_username")
    password = st.text_input("Password", type="password", value=default_password, key="isee_password")
    server = st.selectbox("Server", api.SERVER_RESPONSE, index=1, key="isee_server") # Default to 'EU'
    
    # Display Login/Logout Button
    if st.session_state.get('logged_in', False):
        if st.button("Logout from iSee"):
            # Reset only iSee-related session state on logout
            keys_to_delete = ['session', 'username', 'password', 'database', 'urlserver', 'dbs', 'logged_in', 'df_hierarchy', 'df_listname']
            for key in keys_to_delete:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
    else:
        if st.button("Login to iSee"):
            if username and password:
                with st.spinner("Logging in..."):
                    # The login function now handles UI feedback (errors/success)
                    api.loginAPI(username, password, server)
            else:
                st.warning("Please enter both username and password.")

    # --- Main Content Area for the iSee page ---
    if st.session_state.get('logged_in', False):
        st.success(f"Logged in to iSee as {st.session_state.username}")
        st.markdown("---")

        # --- Database Selection ---
        db_names = [db['name'] for db in st.session_state.get('dbs', [])]
        if db_names:
            selected_db_name = st.selectbox(
                "Select a Database",
                options=db_names,
                index=0 if db_names else None,
                key="db_selection"
            )

            if st.button("Connect to Database"):
                 with st.spinner(f"Connecting to {selected_db_name}..."):
                    if api.select_database(selected_db_name):
                        # Clear old data when connecting to a new DB
                        if 'df_hierarchy' in st.session_state:
                            del st.session_state['df_hierarchy']
                        if 'df_listname' in st.session_state:
                            del st.session_state['df_listname']
        else:
            st.warning("No databases found for this user.")

        # --- Data Fetching Section ---
        if st.session_state.get('database'):
            st.header(f"Database: `{st.session_state.database}`")
            
            if st.button("Fetch Hierarchy Data"):
                # The get_hierarchy method now handles its own spinner and progress
                df_hierarchy, df_listname = api.get_hierarchy()
                if df_hierarchy is not None and df_listname is not None:
                    # Store dataframes in session state to persist them
                    st.session_state['df_hierarchy'] = df_hierarchy
                    st.session_state['df_listname'] = df_listname
            
            # --- Display Data and Download Buttons ---
            if 'df_hierarchy' in st.session_state and 'df_listname' in st.session_state:
                st.subheader("Hierarchy Data Preview")
                st.dataframe(st.session_state['df_hierarchy'])
                
                st.subheader("List Name Data Preview")
                st.dataframe(st.session_state['df_listname'])
                
                st.subheader("Download Data")
                col1, col2 = st.columns(2)
                
                with col1:
                    csv_hierarchy = convert_df_to_csv(st.session_state['df_hierarchy'])
                    st.download_button(
                        label="Download Hierarchy CSV",
                        data=csv_hierarchy,
                        file_name=f"{st.session_state.database}_hierarchy.csv",
                        mime="text/csv",
                    )
                
                with col2:
                    csv_listname = convert_df_to_csv(st.session_state['df_listname'])
                    st.download_button(
                        label="Download List Name CSV",
                        data=csv_listname,
                        file_name=f"{st.session_state.database}_listname.csv",
                        mime="text/csv",
                    )

    elif not st.session_state.get('logged_in', False) and st.session_state.get('username') is not None:
         st.info("Please log in to the iSee API to continue.")

