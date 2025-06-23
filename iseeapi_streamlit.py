import streamlit as st
import requests
import json
import pandas as pd
import os

class Api:
    """
    A class to interact with the iSee API, adapted for use with Streamlit.
    """
    SERVER_RESPONSE = ("US", "EU", "PR")

    def __init__(self):
        """
        Initializes the Api class.
        In a Streamlit context, we'll use st.session_state to manage state.
        """
        if 'session' not in st.session_state:
            st.session_state.session = requests.Session()
            st.session_state.session.headers.update({"Accept-Language": "en", "Accept": "application/json"})
        
        # Initialize other session state variables if they don't exist
        if 'username' not in st.session_state:
            st.session_state.username = ""
        if 'password' not in st.session_state:
            st.session_state.password = ""
        if 'database' not in st.session_state:
            st.session_state.database = None
        if 'urlserver' not in st.session_state:
            st.session_state.urlserver = ""
        if 'dbs' not in st.session_state:
            st.session_state.dbs = []
        if 'logged_in' not in st.session_state:
            st.session_state.logged_in = False

    def loginAPI(self, username, password, server, database=None):
        """
        Handles the login process using credentials and server info from the Streamlit UI.

        Args:
            username (str): The user's username.
            password (str): The user's password.
            server (str): The server to connect to ('US', 'EU', 'PR').
            database (str, optional): The specific database to use. Defaults to None.

        Returns:
            bool: True if login is successful, False otherwise.
        """
        st.session_state.username = username
        st.session_state.password = password

        if server not in self.SERVER_RESPONSE:
            st.error(f"'{server}' is an unknown server. Please choose from {self.SERVER_RESPONSE}.")
            return False
        
        url_map = {"US": "-us", "PR": "-preview", "EU": ""}
        st.session_state.urlserver = url_map[server]

        login_url = f"https://isee{st.session_state.urlserver}.icareweb.com/apiv4/login/"

        try:
            response_login = st.session_state.session.post(
                url=login_url,
                json={"username": st.session_state.username, "password": st.session_state.password},
            )
            response_login.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

        except requests.exceptions.HTTPError as err:
            if err.response.status_code == 400:
                st.error("Incorrect username or password.")
            else:
                st.error(f"An HTTP error occurred: {err}")
            return False
        except requests.exceptions.RequestException as e:
            st.error(f"An error occurred during login: {e}")
            return False

        user_data = response_login.json()
        st.session_state.session.headers["Authorization"] = f"Bearer {user_data['token']}"
        st.session_state.dbs = sorted(user_data.get("dbs", []), key=lambda db: db.get('name', ''))
        st.session_state.logged_in = True
        
        st.success("Login successful!")
        return True

    def select_database(self, db_name):
        """
        Selects a database after a successful login.

        Args:
            db_name (str): The name of the database to select.

        Returns:
            bool: True if the database is selected successfully, False otherwise.
        """
        db_info = next((db for db in st.session_state.dbs if db['name'] == db_name), None)
        if not db_info:
            st.error("Selected database not found.")
            return False
        
        st.session_state.database = db_info['db']
        login_url = f"https://isee{st.session_state.urlserver}.icareweb.com/apiv4/login/"
        choose_url = login_url + st.session_state.database
        
        try:
            response_database = st.session_state.session.get(url=choose_url)
            response_database.raise_for_status()
            
            user_data = response_database.json()
            st.session_state.session.headers["Authorization"] = f"Bearer {user_data['token']}"
            st.info(f"Successfully connected to database: {st.session_state.database}")
            return True
        
        except requests.exceptions.RequestException as e:
            st.error(f"Failed to select database. Status code: {response_database.status_code}, Error: {e}")
            return False

    def get_hierarchy(self):
        """
        Fetches the complete asset hierarchy from the API.

        Returns:
            tuple: A tuple containing two pandas DataFrames (df_hierarchy, df_listname)
                   or (None, None) if an error occurs.
        """
        if not st.session_state.logged_in or not st.session_state.database:
            st.warning("You must be logged in and have a database selected to fetch hierarchy.")
            return None, None
            
        base_url = f"https://isee{st.session_state.urlserver}.icareweb.com/apiv4/assets/"
        hierarchy_list = []
        listname = []
        id_to_name_map = {}
        page = 1
        total_assets = 0

        with st.spinner("Fetching hierarchy data... This may take a moment."):
            try:
                # First call to get metadata
                initial_response = st.session_state.session.get(f"{base_url}?p=1&count=1")
                initial_response.raise_for_status()
                meta = initial_response.json().get('_meta', {})
                total_assets = meta.get('total', 0)
                if total_assets == 0:
                    st.warning("No assets found in the hierarchy.")
                    return pd.DataFrame(), pd.DataFrame()

                progress_bar = st.progress(0)
                processed_assets = 0
                
                while processed_assets < total_assets:
                    response = st.session_state.session.get(f"{base_url}?p={page}&count=1000")
                    response.raise_for_status()
                    assets_data = response.json()
                    
                    if not assets_data.get('_embedded'):
                        break # No more assets

                    for asset in assets_data['_embedded']:
                        # Process listname
                        asset_info = {'_id': asset['_id'], 'name': asset['name']}
                        optionals = asset.get('optionals', {})
                        if 'mac' in optionals:
                            asset_info['mac'] = optionals['mac']
                        elif 'coordinators' in optionals and optionals['coordinators']:
                             asset_info['mac'] = optionals['coordinators'][0].replace(':', '').lower()
                        # Add other optional fields as needed
                        listname.append(asset_info)

                        id_to_name_map[asset['_id']] = asset['name']

                        # Process hierarchy
                        path_info = {"paths": asset['path'], "name": asset['name'], "_id": asset['_id'], "type": asset['t']}
                        hierarchy_list.append(path_info)
                        
                        processed_assets += 1
                    
                    progress_bar.progress(min(processed_assets / total_assets, 1.0))
                    page += 1

                # Now that we have the full id_to_name_map, resolve paths
                for item in hierarchy_list:
                    for i, path_id in enumerate(item['paths']):
                        item[f"level{i+1}"] = id_to_name_map.get(path_id, "Unknown Path ID")

                df_hierarchy = pd.DataFrame(hierarchy_list)
                df_listname = pd.DataFrame(listname)

                # Post-processing the hierarchy DataFrame
                if not df_hierarchy.empty:
                    cols = [c for c in df_hierarchy.columns if c.startswith('level')]
                    other_cols = ['name', '_id', 'type', 'paths']
                    df_hierarchy = df_hierarchy[sorted(cols) + [c for c in other_cols if c in df_hierarchy.columns]]
                    if 'level1' in df_hierarchy.columns:
                        df_hierarchy = df_hierarchy[df_hierarchy['level1'] != 'Recycle bin'].reset_index(drop=True)

                st.success(f"Successfully extracted {processed_assets} assets.")
                
                # --- Advanced Hierarchy Processing (Factory, Asset, Zone) ---
                df_hierarchy = self._process_entity(df_hierarchy, 16777221, 'Factory')
                df_hierarchy = self._process_entity(df_hierarchy, 33554432, 'Asset')
                df_hierarchy = self._process_entity(df_hierarchy, 16777222, 'Zone')
                
                return df_hierarchy.drop(columns=['paths'], errors='ignore'), df_listname

            except requests.exceptions.RequestException as e:
                st.error(f"An error occurred while fetching hierarchy: {e}")
                return None, None
            except Exception as e:
                st.error(f"An unexpected error occurred during hierarchy processing: {e}")
                return None, None

    def _process_entity(self, df_hierarchy, entity_type, entity_name):
        """Helper function to process and merge factory, asset, or zone information."""
        try:
            df_entity = df_hierarchy[df_hierarchy['type'] == entity_type]
            if df_entity.empty:
                st.info(f"No entities of type '{entity_name}' found.")
                df_hierarchy[f'{entity_name}_id'] = 'noid'
                df_hierarchy[f'{entity_name.lower()}_name'] = 'noname'
                return df_hierarchy

            entity_id_list = df_entity['_id'].unique().tolist()

            def get_entity_id(path):
                intersection = set(entity_id_list).intersection(path)
                return max(intersection, default='noid')

            df_hierarchy[f'{entity_name}_id'] = df_hierarchy['paths'].apply(get_entity_id)
            
            df_entity_name = df_entity[['_id', 'name']].rename(columns={'_id': f'{entity_name}_id', 'name': f'{entity_name.lower()}_name'})

            df_hierarchy = pd.merge(df_hierarchy, df_entity_name, on=f'{entity_name}_id', how='left')
            df_hierarchy[f'{entity_name.lower()}_name'].fillna('noname', inplace=True)
            st.success(f"Processed {entity_name} information.")

        except Exception as e:
            st.warning(f"Could not process {entity_name} information. Error: {e}")
            df_hierarchy[f'{entity_name}_id'] = 'noid'
            df_hierarchy[f'{entity_name.lower()}_name'] = 'noname'
            
        return df_hierarchy
