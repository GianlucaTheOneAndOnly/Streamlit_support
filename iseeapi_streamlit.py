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
        Initializes the Api class using st.session_state to manage state.
        """
        if 'session' not in st.session_state:
            st.session_state.session = requests.Session()
            # CORRECTION: Ajouter des headers plus complets
            st.session_state.session.headers.update({
                "Accept-Language": "en",
                "Accept": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Content-Type": "application/json"
            })
        
        # Initialize other session state variables if they don't exist
        if 'username' not in st.session_state: st.session_state.username = ""
        if 'password' not in st.session_state: st.session_state.password = ""
        if 'database' not in st.session_state: st.session_state.database = None
        if 'urlserver' not in st.session_state: st.session_state.urlserver = ""
        if 'dbs' not in st.session_state: st.session_state.dbs = []
        if 'logged_in' not in st.session_state: st.session_state.logged_in = False

    def loginAPI(self, username, password, server, database=None):
        """
        Handles the login process using credentials and server info from the Streamlit UI.
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
            response_login.raise_for_status()

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
        """
        db_info = next((db for db in st.session_state.dbs if db['name'] == db_name), None)
        if not db_info:
            st.error("Selected database not found.")
            return False
        
        st.session_state.database = db_info['db']
        login_url = f"https://isee{st.session_state.urlserver}.icareweb.com/apiv4/login/"
        choose_url = login_url + st.session_state.database
        
        st.write(f"🔍 Debug: Connecting to URL: {choose_url}")
        
        try:
            response_database = st.session_state.session.get(url=choose_url)
            
            # Log pour debug
            st.write(f"🔍 Debug: Database selection response status: {response_database.status_code}")
            if response_database.status_code != 200:
                st.write(f"🔍 Debug: Response text: {response_database.text}")
            
            response_database.raise_for_status()
            
            user_data = response_database.json()
            
            # Vérifier que nous avons reçu un nouveau token
            if 'token' not in user_data:
                st.error("No token received from database selection.")
                return False
                
            # Update the authorization token to be database-specific
            new_token = user_data['token']
            st.session_state.session.headers["Authorization"] = f"Bearer {new_token}"
            
            st.write(f"🔍 Debug: New token received (first 20 chars): {new_token[:20]}...")

            # Clear session cookies after getting the DB-specific token.
            st.session_state.session.cookies.clear()
            
            st.success(f"✅ Successfully connected to database: {st.session_state.database}")
            return True
    
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                st.error("❌ Access forbidden to this database. Check your permissions.")
            elif e.response.status_code == 404:
                st.error("❌ Database not found. The database ID may be incorrect.")
            else:
                status_code = e.response.status_code if e.response else "N/A"
                st.error(f"❌ Failed to select database. Status code: {status_code}, Error: {e}")
            return False
        except requests.exceptions.RequestException as e:
            st.error(f"❌ Network error while selecting database: {e}")
            return False

    def get_hierarchy(self):
        """
        Fetches the complete asset hierarchy from the API.
        """
        st.write("🔍 Debug - Checking session state:")
        st.write(f"- Username: {st.session_state.get('username', 'MISSING')}")
        st.write(f"- Database: {st.session_state.get('database', 'MISSING')}")
        st.write(f"- URL Server: {st.session_state.get('urlserver', 'MISSING')}")
        st.write(f"- Logged in: {st.session_state.get('logged_in', False)}")


        if not st.session_state.logged_in or not st.session_state.database:
            st.warning("You must be logged in and have a database selected to fetch hierarchy.")
            return None, None
        
        # Vérifier que nous avons un token d'autorisation
        if 'Authorization' not in st.session_state.session.headers:
            st.error("No authorization token found. Please reconnect to the database.")
            return None, None
            
        base_url = f"https://isee{st.session_state.urlserver}.icareweb.com/apiv4/{st.session_state.database}/assets/"
        
        hierarchy_list = []
        listname = []
        id_to_name_map = {}
        page = 1
        
        with st.spinner("Fetching hierarchy data... This may take a moment."):
            try:
                # Afficher les informations de debug
                st.write(f"🔍 Debug: Calling URL: {base_url}?p=1&count=1")
                st.write(f"🔍 Debug: Authorization header present: {'Authorization' in st.session_state.session.headers}")
                
                # First call to get metadata
                initial_response = st.session_state.session.get(f"{base_url}?p=1&count=1")
                
                # Log des détails de la réponse pour le debug
                st.write(f"🔍 Debug: Response status code: {initial_response.status_code}")
                if initial_response.status_code != 200:
                    st.write(f"🔍 Debug: Response text: {initial_response.text}")
                    
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
                        break

                    for asset in assets_data['_embedded']:
                        asset_info = {'_id': asset['_id'], 'name': asset['name']}
                        optionals = asset.get('optionals', {})
                        if 'mac' in optionals:
                            asset_info['mac'] = optionals['mac']
                        elif 'coordinators' in optionals and optionals['coordinators']:
                            asset_info['mac'] = optionals['coordinators'][0].replace(':', '').lower()
                        listname.append(asset_info)

                        id_to_name_map[asset['_id']] = asset['name']

                        path_info = {"paths": asset['path'], "name": asset['name'], "_id": asset['_id'], "type": asset['t']}
                        hierarchy_list.append(path_info)
                        
                        processed_assets += 1
                    
                    progress_bar.progress(min(processed_assets / total_assets, 1.0))
                    page += 1

                for item in hierarchy_list:
                    for i, path_id in enumerate(item['paths']):
                        item[f"level{i+1}"] = id_to_name_map.get(path_id, "Unknown Path ID")

                df_hierarchy = pd.DataFrame(hierarchy_list)
                df_listname = pd.DataFrame(listname)

                if not df_hierarchy.empty:
                    cols = [c for c in df_hierarchy.columns if c.startswith('level')]
                    other_cols = ['name', '_id', 'type', 'paths']
                    df_hierarchy = df_hierarchy[sorted(cols) + [c for c in other_cols if c in df_hierarchy.columns]]
                    if 'level1' in df_hierarchy.columns:
                        df_hierarchy = df_hierarchy[df_hierarchy['level1'] != 'Recycle bin'].reset_index(drop=True)

                st.success(f"Successfully extracted {processed_assets} assets.")
                
                df_hierarchy = self._process_entity(df_hierarchy, 16777221, 'Factory')
                df_hierarchy = self._process_entity(df_hierarchy, 33554432, 'Asset')
                df_hierarchy = self._process_entity(df_hierarchy, 16777222, 'Zone')
                
                return df_hierarchy.drop(columns=['paths'], errors='ignore'), df_listname

            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 403:
                    st.error("❌ Access forbidden. Possible causes:")
                    st.error("• Your user account doesn't have permission to access assets in this database")
                    st.error("• The authorization token has expired")
                    st.error("• The database ID is incorrect")
                    st.error("💡 Try reconnecting to the database or contact your administrator for permissions.")
                else:
                    st.error(f"An HTTP error occurred: {e}")
                return None, None
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

        except Exception as e:
            st.warning(f"Could not process {entity_name} information. Error: {e}")
            df_hierarchy[f'{entity_name}_id'] = 'noid'
            df_hierarchy[f'{entity_name.lower()}_name'] = 'noname'
            
        return df_hierarchy
    
    def test_api_access(self):
        """
        Teste l'accès à différents endpoints pour diagnostiquer le problème
        """
        if not st.session_state.logged_in or not st.session_state.database:
            st.warning("You must be logged in and have a database selected.")
            return
        
        base_url = f"https://isee{st.session_state.urlserver}.icareweb.com/apiv4/{st.session_state.database}"
        
        # Endpoints à tester par ordre de complexité
        endpoints = [
            ("Database Info", ""),
            ("User Info", "/user"),
            ("Assets (single)", "/assets/?p=1&count=1"),
            ("Assets (small batch)", "/assets/?p=1&count=10")
        ]
        
        st.subheader("🧪 API Access Test")
        
        for name, endpoint in endpoints:
            test_url = base_url + endpoint
            try:
                st.write(f"Testing {name}: `{test_url}`")
                response = st.session_state.session.get(test_url)
                
                if response.status_code == 200:
                    st.success(f"✅ {name}: SUCCESS")
                    if endpoint == "":  # Database info
                        data = response.json()
                        st.write(f"Database name: {data.get('name', 'Unknown')}")
                elif response.status_code == 403:
                    st.error(f"❌ {name}: FORBIDDEN")
                    st.write(f"Response: {response.text[:200]}...")
                else:
                    st.warning(f"⚠️ {name}: Status {response.status_code}")
                    st.write(f"Response: {response.text[:200]}...")
                    
            except Exception as e:
                st.error(f"❌ {name}: ERROR - {e}")
            
            st.write("---")