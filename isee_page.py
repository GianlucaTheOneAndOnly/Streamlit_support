import streamlit as st
import pandas as pd
from iseeapi_streamlit_old import Api  # Assumes iseeapi_streamlit.py is in the same directory
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

        with st.expander("🔧 Debug - Session State"):
            st.write("**Données stockées dans st.session_state :**")
            st.write(f"- Username: {st.session_state.get('username', 'NOT SET')}")
            st.write(f"- Password: {'***' if st.session_state.get('password') else 'NOT SET'}")
            st.write(f"- Server URL suffix: {st.session_state.get('urlserver', 'NOT SET')}")
            st.write(f"- Database ID: {st.session_state.get('database', 'NOT SET')}")
            st.write(f"- Logged in: {st.session_state.get('logged_in', False)}")
            st.write(f"- Number of databases: {len(st.session_state.get('dbs', []))}")
            st.write(f"- Session object exists: {'session' in st.session_state}")
            st.write(f"- Authorization header: {'Authorization' in st.session_state.session.headers if 'session' in st.session_state else 'NO SESSION'}")




        st.success(f"✅ Logged in to iSee as {st.session_state.username}")
        if st.button("Logout from iSee"):
            # Reset only iSee-related session state on logout
            keys_to_delete = ['session', 'username', 'password', 'database', 'urlserver', 'dbs', 'logged_in', 'df_hierarchy', 'df_listname', 'database_selected']
            for key in keys_to_delete:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
    else:
        if st.button("Login to iSee"):
            if username and password:
                with st.spinner("Logging in..."):
                    # The login function now handles UI feedback (errors/success)
                    success = api.loginAPI(username, password, server)
                    if success:
                        st.rerun()  # Refresh to show database selection
            else:
                st.warning("Please enter both username and password.")

    # --- Main Content Area for the iSee page ---
    if st.session_state.get('logged_in', False):
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

            if st.button("Connect to Database") or not st.session_state.get('database_selected', False):
                with st.spinner(f"Connecting to {selected_db_name}..."):
                    if api.select_database(selected_db_name):
                        st.session_state['database_selected'] = True
                        # Clear old data when connecting to a new DB
                        if 'df_hierarchy' in st.session_state:
                            del st.session_state['df_hierarchy']
                        if 'df_listname' in st.session_state:
                            del st.session_state['df_listname']
                        st.rerun()  # Refresh to show fetch button
        else:
            st.warning("No databases found for this user.")

        # --- Data Fetching Section ---
        if st.session_state.get('database') and st.session_state.get('database_selected', False):

            st.success(f"✅ Connected to database: `{st.session_state.database}`")
            st.markdown("---")
            
            # Add debug info
            with st.expander("🔧 Debug Information"):
                st.write("**Session State Debug:**")
                st.write(f"- Username: {st.session_state.get('username', 'Not set')}")
                st.write(f"- Server URL: {st.session_state.get('urlserver', 'Not set')}")
                st.write(f"- Database ID: {st.session_state.get('database', 'Not set')}")
                st.write(f"- Number of available databases: {len(st.session_state.get('dbs', []))}")
                
                # Show the complete URL that will be used
                if st.session_state.get('database') and st.session_state.get('urlserver') is not None:
                    hierarchy_url = f"https://isee{st.session_state.urlserver}.icareweb.com/apiv4/{st.session_state.database}/assets/"
                    st.write(f"- Hierarchy URL: `{hierarchy_url}`")
            
            if st.button("🔄 Fetch Hierarchy Data"):
                # The get_hierarchy method now handles its own spinner and progress
                df_hierarchy, df_listname = api.get_hierarchy()
                if df_hierarchy is not None and df_listname is not None:
                    # Store dataframes in session state to persist them
                    st.session_state['df_hierarchy'] = df_hierarchy
                    st.session_state['df_listname'] = df_listname
                    st.rerun()  # Refresh to show the data
            

            if st.button("🧪 Diagnostic complet API"):
                api.run_diagnostic()

            if st.button("🧪 Test API Access"):
                api.test_api_access()

            if st.button("Database selection method"):
                api.check_database_selection_method()

            # --- Display Data and Download Buttons ---
            if 'df_hierarchy' in st.session_state and 'df_listname' in st.session_state:
                st.success(f"✅ Data fetched successfully!")
                
                # Show data statistics
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Hierarchy Records", len(st.session_state['df_hierarchy']))
                with col2:
                    st.metric("Asset Records", len(st.session_state['df_listname']))
                
                st.subheader("📊 Hierarchy Data Preview")
                st.dataframe(st.session_state['df_hierarchy'].head(10))  # Show only first 10 rows
                
                st.subheader("📋 List Name Data Preview")
                st.dataframe(st.session_state['df_listname'].head(10))  # Show only first 10 rows
                
                st.subheader("💾 Download Data")
                col1, col2 = st.columns(2)
                
                with col1:
                    csv_hierarchy = convert_df_to_csv(st.session_state['df_hierarchy'])
                    st.download_button(
                        label="📥 Download Hierarchy CSV",
                        data=csv_hierarchy,
                        file_name=f"{st.session_state.database}_hierarchy.csv",
                        mime="text/csv",
                    )
                
                with col2:
                    csv_listname = convert_df_to_csv(st.session_state['df_listname'])
                    st.download_button(
                        label="📥 Download List Name CSV",
                        data=csv_listname,
                        file_name=f"{st.session_state.database}_listname.csv",
                        mime="text/csv",
                    )

    elif not st.session_state.get('logged_in', False) and st.session_state.get('username') is not None:
         st.info("ℹ️ Please log in to the iSee API to continue.")

# For debugging - you can run this directly
if __name__ == "__main__":
    show()