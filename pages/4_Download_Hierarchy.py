import streamlit as st
import pandas as pd
from src.api import Api  # Your existing API class file
from src.auth import secure_page

# Cache CSV conversion for better performance
@st.cache_data
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')


@secure_page
def render_hierarchy_page():
    st.title("I-CARE API Data Extractor")
    st.markdown("Connect to the iSee API, fetch asset hierarchy, and download data as CSV files.")

    # Initialize session state keys if missing
    for key in ['username', 'password', 'server', 'logged_in', 'dbs', 'database', 'database_selected', 'df_hierarchy', 'df_listname', 'api_client']:
        if key not in st.session_state:
            st.session_state[key] = None if key not in ['logged_in', 'database_selected'] else False

    # Initialize or reuse API client properly
    if st.session_state.api_client is not None:
        api = st.session_state.api_client
    elif st.session_state.username and st.session_state.password and st.session_state.server:
        #api = Api(st.session_state.username, st.session_state.password, st.session_state.server)
        api = Api(st.session_state.username, st.session_state.password)
    else:
        api = None

    # Try to load default credentials from secrets if available
    try:
        default_username = st.secrets["credentials"]["username"]
        default_password = st.secrets["credentials"]["password"]
    except (KeyError, AttributeError):
        default_username = ""
        default_password = ""

    # --- Login Section ---
    st.subheader("Login Credentials")

    username = st.text_input("Username", value=st.session_state.username or default_username, key="username")
    password = st.text_input("Password", type="password", value=st.session_state.password or default_password, key="password")
    server = st.selectbox("Select Server", Api.SERVER_RESPONSE, index=1 if st.session_state.server is None else Api.SERVER_RESPONSE.index(st.session_state.server), key="server")

    if st.session_state.logged_in:
        with st.expander("🔧 Debug - Session State"):
            st.write(st.session_state)

        st.success(f"✅ Logged in as {st.session_state.username}")

        # Database switching section - only show when logged in
        st.markdown("---")
        st.subheader("Database Selection")
        
        if st.session_state.dbs:
            db_names = [db['name'] for db in st.session_state.dbs]
            current_db_index = 0
            if st.session_state.database:
                try:
                    current_db_index = db_names.index(st.session_state.database)
                except ValueError:
                    current_db_index = 0
            
            selected_db_name = st.selectbox(
                "Current Database", 
                db_names, 
                index=current_db_index,
                key="current_db_selection"
            )
            
            # Show current database status
            if st.session_state.database:
                st.info(f"Currently connected to: **{st.session_state.database}**")
            
            # Button to switch database
            if selected_db_name != st.session_state.database:
                if st.button(f"Switch to Database: {selected_db_name}"):
                    selected_db = next((db for db in st.session_state.dbs if db['name'] == selected_db_name), None)
                    if selected_db:
                        with st.spinner(f"Switching to database {selected_db_name}..."):
                            success = st.session_state.api_client.login_step2_select_db(selected_db['db'])
                            if success is True:
                                st.session_state.database = selected_db_name
                                # Clear old hierarchy data when switching databases
                                st.session_state.df_hierarchy = None
                                st.session_state.df_listname = None
                                st.success(f"Successfully switched to database: {selected_db_name}")
                                st.rerun()
                            else:
                                st.error(f"Failed to switch database: {success}")
                    else:
                        st.error("Selected database not found.")

        if st.button("Logout"):
            # Clear all iSee-related session state on logout
            keys_to_clear = [
                'username', 'password', 'server', 'logged_in', 'dbs', 'database', 'database_selected',
                'df_hierarchy', 'df_listname', 'api_client'
            ]
            for key in keys_to_clear:
                st.session_state[key] = None if key not in ['logged_in', 'database_selected'] else False
            st.rerun()
    else:
        if st.button("Login"):
            if username and password:
                with st.spinner("Logging in..."):
                    # Create new Api instance with credentials
                    api = Api(username, password)
                    db_list = api.login_step1_get_dbs(server)
                    if isinstance(db_list, list):
                        st.session_state.api_client = api
                        st.session_state.dbs = db_list
                        st.success("Login successful! Please select a database below.")
                    else:
                        st.error(db_list)  # error message from API
            else:
                st.warning("Please enter both username and password.")

    # --- Initial Database Selection (only when not logged in but have dbs) ---
    if st.session_state.dbs and not st.session_state.logged_in:
        st.markdown("---")
        st.subheader("Initial Database Selection")
        db_names = [db['name'] for db in st.session_state.dbs]
        selected_db_name = st.selectbox("Select Database", db_names, key="db_selection")

        if st.button("Connect to Database"):
            selected_db = next((db for db in st.session_state.dbs if db['name'] == selected_db_name), None)
            if selected_db:
                with st.spinner(f"Connecting to database {selected_db_name}..."):
                    success = st.session_state.api_client.login_step2_select_db(selected_db['db'])
                    if success is True:
                        st.session_state.database = selected_db_name
                        st.session_state.logged_in = True
                        st.session_state.database_selected = True
                        # Clear old data on new DB connect
                        st.session_state.df_hierarchy = None
                        st.session_state.df_listname = None
                        st.success(f"Connected to database: {selected_db_name}")
                        st.rerun()
                    else:
                        st.error(success)
            else:
                st.error("Selected database not found.")

    # --- Main content after login ---
    if st.session_state.logged_in and st.session_state.database:
        st.markdown("---")
        st.subheader("Data Operations")

        # Debug info
        with st.expander("🔧 Debug Information"):
            st.write("Session state data:")
            st.write(st.session_state)

        # Fetch hierarchy button
        if st.button("Fetch Asset Hierarchy"):
            with st.spinner("Fetching hierarchy data..."):
                h_df, l_df = st.session_state.api_client.get_hierarchy()
                if h_df is not None and l_df is not None:
                    st.session_state.df_hierarchy = h_df
                    st.session_state.df_listname = l_df
                    st.success("Data fetched successfully!")
                    st.rerun()
                else:
                    st.error("Failed to fetch hierarchy data.")

        # Display data and download options
        if st.session_state.df_hierarchy is not None and st.session_state.df_listname is not None:
            st.markdown("---")
            st.subheader("Data Summary")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Hierarchy records", len(st.session_state.df_hierarchy))
            with col2:
                st.metric("Asset records", len(st.session_state.df_listname))

            st.subheader("Hierarchy Data Preview")
            st.dataframe(st.session_state.df_hierarchy.head(10))

            st.subheader("List Name Data Preview")
            st.dataframe(st.session_state.df_listname.head(10))

            st.subheader("Download Data")
            col1, col2 = st.columns(2)
            with col1:
                csv_hierarchy = convert_df_to_csv(st.session_state.df_hierarchy)
                st.download_button(
                    label="Download Hierarchy CSV",
                    data=csv_hierarchy,
                    file_name=f"{st.session_state.database}_hierarchy.csv",
                    mime="text/csv",
                )
            with col2:
                csv_listname = convert_df_to_csv(st.session_state.df_listname)
                st.download_button(
                    label="Download List Name CSV",
                    data=csv_listname,
                    file_name=f"{st.session_state.database}_listname.csv",
                    mime="text/csv",
                )
    elif st.session_state.logged_in:
        st.info("Please select a database to continue.")
    else:
        st.info("Please login to continue.")


    
render_hierarchy_page()