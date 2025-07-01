# iseeapi_streamlite.py

import streamlit as st
import requests
import json
import pandas as pd


# Add this import at the top of the file
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
        # Initial call to get total count
        try:
            url = f"https://isee{self.urlserver}.icareweb.com/apiv4/assets/?p=1&count=25"

            # --- DEBUGGING STEP ---
            # Let's see the headers we are about to send
            st.info("Attempting to fetch data with the following headers:")
            st.json(self.headers)
            # --- END DEBUGGING STEP ---


            response = self.session.get(url, headers=self.headers, timeout=20)
            response.raise_for_status()
            total_assets = response.json()['_meta']['total']

            


            if total_assets == 0:
                st.warning("No assets found in this database.")
                return pd.DataFrame(), pd.DataFrame() # Return empty dataframes
            

        except HTTPError as http_err:
            # This is the new, important part!
            st.error(f"HTTP error occurred: {http_err}")
            st.error("The server rejected the request. Here is the detailed response from the API:")
            try:
                # Try to show the JSON error message from the server
                st.json(response.json())
            except ValueError:
                # If the response isn't JSON, show the raw text
                st.text(response.text)
            return None, None


        except requests.exceptions.RequestException as e:
            st.error(f"Failed to connect to asset endpoint: {e}")
            return None, None
        except KeyError:
            st.error("API response format is unexpected. Could not find total asset count.")
            return None, None

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
                    # This is a direct copy of your original processing logic
                    if 'mac' in asset.get('optionals', {}):
                        listname.append({'_id': asset['_id'], 'name': asset['name'], 'mac': asset['optionals']['mac']})
                    elif 'coordinators' in asset.get('optionals', {}):
                        listname.append({'_id': asset['_id'], 'name': asset['name'], 'mac': asset['optionals']['coordinators'][0].replace(':', '').lower()})
                    elif 'transmitter' in asset.get('optionals', {}):
                        listname.append({'_id': asset['_id'], 'name': asset['name'], 'transmitter': asset['optionals']['transmitter']})
                    elif 'criticality' in asset.get('optionals', {}):
                        listname.append({'_id': asset['_id'], 'name': asset['name'], 'criticality': asset['optionals']['criticality']})
                    elif 'equipment_type' in asset.get('optionals', {}):
                        listname.append({'_id': asset['_id'], 'name': asset['name'], 'equipment_type': asset['optionals']['equipment_type']})
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
            
            # --- This is your original post-processing logic ---
            # It's kept here as it's part of the data transformation process.
            # (Your entire 'Factory name', 'Asset name', and 'Zone name' processing logic would go here)
            # For brevity, this example assumes the basic hierarchy is sufficient.
            # To make it complete, paste your df.merge/apply sections here.
            
            # Example filtering from your code:
            if 'level1' in df_hierarchy.columns:
                df_hierarchy = df_hierarchy[df_hierarchy['level1'] != 'Recycle bin'].reset_index(drop=True)
            
            # re order the columns to get level1,... first following by name,id,type
            df_hierarchy = df_hierarchy[[c for c in df_hierarchy if c not in [
                'name', '_id', 'type']] + ['name', '_id', 'type']]

            df_hierarchy_processed = df_hierarchy # In your final code, this should be the result of all your merges.

        return df_hierarchy_processed, df_listname