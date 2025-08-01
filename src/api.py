# iseeapi_streamlite.py

import streamlit as st
import requests
import json
import pandas as pd
from requests.exceptions import HTTPError

class Api:
    """
    Handles all communication with the I-CARE API, including authentication
    and data processing.
    """
    SERVER_RESPONSE = ("EU", "US", "PR")
    username = None
    password = None

    def __init__(self,username,password):
        self.username = username
        self.password = password
        self.database = None
        self.headers = {"Accept-Language": "en", "Accept": "application/json"}
        self.urlserver = None
        self.session = requests.session()

    def login_step1_get_dbs(self, server: str):
        """
        Performs the first part of the login: server selection and initial token retrieval.
        Returns a list of available databases on success or an error message string on failure.
        """
        if server not in self.SERVER_RESPONSE:
            return f"'{server}' is an unknown server."

        if server == "US":
            self.urlserver = "-us"
        elif server == "PR":
            self.urlserver = "-preview"
        else: # "EU"
            self.urlserver = ""

        loginurl = f"https://isee{self.urlserver}.icareweb.com/apiv4/login/"

        try:
            response_login = self.session.post(
                url=loginurl,
                json={"username": self.username, "password": self.password},
                headers=self.headers,
                timeout=20 # Add a timeout
            )
            response_login.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

            user = response_login.json()
            self.headers["Authorization"] = f"Bearer {user['token']}"
            dbs = sorted(user.get("dbs", []), key=lambda db: db['name'])
            return dbs
        except requests.exceptions.RequestException as e:
            return f"Login failed. A network error occurred: {e}"
        except Exception as e:
            return f"An unexpected error occurred during login: {e}"


    def login_step2_select_db(self, db_id: str):
        """
        Performs the second part of the login: database selection and final token retrieval.
        Returns True on success or an error message string on failure.
        """
        self.database = db_id
        loginurl = f"https://isee{self.urlserver}.icareweb.com/apiv4/login/"
        chooseurl = loginurl + self.database

        try:
            response_database = self.session.get(url=chooseurl, headers=self.headers, timeout=20)
            response_database.raise_for_status()

            user = response_database.json()
            self.headers["Authorization"] = f"Bearer {user['token']}"
            return True
        except requests.exceptions.RequestException as e:
            return f"Database selection failed. A network error occurred: {e}"
        except Exception as e:
            return f"An unexpected error occurred selecting the database: {e}"


    def get_hierarchy(self):
        """
        Fetches and processes the asset hierarchy. Uses st.progress for UI feedback.
        Returns two DataFrames (hierarchy, listname) on success, or (None, None) on failure.
        """
        # ... (The initial data fetching part remains the same) ...
        try:
            url = f"https://isee{self.urlserver}.icareweb.com/apiv4/assets/?p=1&count=25"
            response = self.session.get(url, headers=self.headers, timeout=20)
            response.raise_for_status()
            total_assets = response.json()['_meta']['total']
            if total_assets == 0:
                st.warning("No assets found in this database.")
                return pd.DataFrame(), pd.DataFrame()
        except Exception as e:
            # Simplified error handling for brevity
            st.error(f"Failed to fetch initial asset data: {e}")
            return None, None

        # ... (The while loop for paginating through assets remains the same) ...
        page = 1
        nbr_assets = 0
        dictoname = {}
        hierarchy = []
        listname = []
        progress_bar = st.progress(0, text=f"Preparing to fetch {total_assets} assets...")
        with st.spinner("Fetching data from API..."):
            while nbr_assets < total_assets:
                url = f"https://isee{self.urlserver}.icareweb.com/apiv4/assets/?p={page}&count=1000"
                response = self.session.get(url, headers=self.headers)
                if response.status_code != 200:
                    st.error(f"Error fetching page {page}. Status: {response.status_code}")
                    break
                assets_data = response.json()
                for asset in assets_data.get('_embedded', []):
                    # ... (The asset processing logic inside the loop is unchanged) ...
                    if 'mac' in asset.get('optionals', {}):
                        listname.append({'_id': asset['_id'], 'name': asset['name'], 'mac': asset['optionals']['mac']})
                    elif 'coordinators' in asset.get('optionals', {}):
                        listname.append({'_id': asset['_id'], 'name': asset['name'], 'mac': asset['optionals']['coordinators'][0].replace(':', '').lower()})
                    # ... etc ...
                    else:
                        listname.append({'_id': asset['_id'], 'name': asset['name'], 'criticality': "", 'equipment_type': ""})
                    dictoname[asset['_id']] = asset['name']
                    path_info = {"paths": asset['path'], "name": asset['name'], "_id": asset['_id'], "type": asset['t']}
                    for i, path_id in enumerate(asset['path'], 1):
                        path_info[f"level{i}"] = dictoname.get(path_id, "Unknown Path ID")
                    hierarchy.append(path_info)
                    nbr_assets += 1
                page += 1
                progress_bar.progress(min(nbr_assets / total_assets, 1.0), text=f"Fetched {nbr_assets} / {total_assets} assets...")
        progress_bar.empty()
        if not hierarchy:
            st.warning("No hierarchy data was extracted.")
            return None, None

        # --- Pandas Processing ---
        with st.spinner("Processing data with Pandas..."):
            df_hierarchy = pd.DataFrame(hierarchy)
            df_listname = pd.DataFrame(listname)
            
            if 'level1' in df_hierarchy.columns:
                df_hierarchy = df_hierarchy[df_hierarchy['level1'] != 'Recycle bin'].reset_index(drop=True)
            
            # Make a copy to work with
            df_processed = df_hierarchy.copy()

            # Define the helper function once to be used by all blocks
            def get_string_from_list(list_elem):
                return str(max(list_elem, default='noid'))

            # ------------------- Factory Extraction -------------------
            try:
                df_factory = df_hierarchy[df_hierarchy['type'] == 16777221]
                factory_id_list = df_factory['_id'].unique().tolist()
                def get_factory_id(path):
                    return list(set(factory_id_list).intersection(path))
                df_processed['Factory_id'] = df_processed['paths'].apply(get_factory_id)
                df_processed['Factory_id'] = df_processed['Factory_id'].apply(get_string_from_list)
                df_factory = df_factory[['name', '_id']].rename(columns={'name': 'factory_name', '_id': 'Factory_id'})
                print("factory ", len(df_factory))
                df_processed = pd.merge(df_processed, df_factory, on='Factory_id', how='left')
            except Exception as e:
                print('no factory extracted ', e)
                df_processed['Factory_id'] = 'nullFid'
                df_processed['factory_name'] = 'nullFn'
            
            # ------------------- Asset Extraction -------------------
            try:
                df_asset = df_hierarchy[df_hierarchy['type'] == 33554432]
                asset_id_list = df_asset['_id'].unique().tolist()
                def get_asset_id(path):
                    return list(set(asset_id_list).intersection(path))
                df_processed['Asset_id'] = df_processed['paths'].apply(get_asset_id)
                df_processed['Asset_id'] = df_processed['Asset_id'].apply(get_string_from_list)
                df_asset = df_asset[['name', '_id']].rename(columns={'name': 'asset_name', '_id': 'Asset_id'})
                print("asset ", len(df_asset))
                df_processed = pd.merge(df_processed, df_asset, on='Asset_id', how='left')
            except Exception as e:
                print('no asset extracted ', e)
                df_processed['Asset_id'] = 'null_Aid'
                df_processed['asset_name'] = 'nullAn'

            # ------------------- Zone Extraction -------------------
            try:
                df_zone = df_hierarchy[df_hierarchy['type'] == 16777222]
                zone_id_list = df_zone['_id'].unique().tolist()
                def get_zone_id(path):
                    return list(set(zone_id_list).intersection(path))
                df_processed['Zone_id'] = df_processed['paths'].apply(get_zone_id)
                df_processed['Zone_id'] = df_processed['Zone_id'].apply(get_string_from_list)
                df_zone = df_zone[['name', '_id']].rename(columns={'name': 'zone_name', '_id': 'Zone_id'})
                print("zone ", len(df_zone))
                df_processed = pd.merge(df_processed, df_zone, on='Zone_id', how='left')
            except Exception as e:
                print("No zone extract", e)
                df_processed['Zone_id'] = 'nullZid'
                df_processed['zone_name'] = 'nullZn'

            # --- Final Column Reordering ---
            end_columns = [
                'name', '_id', 'type', 
                'Factory_id', 'factory_name', 
                'Asset_id', 'asset_name', 
                'Zone_id', 'zone_name'
            ]
            front_columns = [col for col in df_processed.columns if col not in end_columns]
            df_processed = df_processed[front_columns + end_columns]
            
        return df_processed, df_listname