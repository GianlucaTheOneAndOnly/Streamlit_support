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
            # Headers plus complets
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
        CORRECTED: Selects a database after a successful login.
        """
        # Vérifications initiales
        if 'dbs' not in st.session_state or not st.session_state.dbs:
            st.error("❌ Aucune base de données disponible en session. Avez-vous bien effectué la connexion ?")
            return False

        if 'urlserver' not in st.session_state or st.session_state.urlserver is None:
            st.error("❌ Le serveur n'est pas défini. Impossible de construire l'URL.")
            return False

        if 'session' not in st.session_state or st.session_state.session is None:
            st.error("❌ La session de requête n'est pas initialisée.")
            return False

        # Rechercher la base sélectionnée dans la liste
        db_info = next((db for db in st.session_state.dbs if db['name'] == db_name), None)
        if not db_info:
            st.error("❌ Base de données sélectionnée introuvable.")
            return False

        # CORRECTION PRINCIPALE: Utiliser le nom technique de la base (db_info['db'])
        st.session_state.database = db_info['db']
        st.session_state.session.headers["X-ICARE-DB"] = db_info["db"]

        # CORRECTION: Construire l'URL correctement - POST au lieu de GET
        login_url = f"https://isee{st.session_state.urlserver}.icareweb.com/apiv4/login/"
        
        st.write(f"🔍 Debug: Sélection de la base '{db_name}' (DB: {st.session_state.database})")
        st.write(f"🔍 Debug: URL de login: `{login_url}`")

        try:
            # CORRECTION: Utiliser POST avec le nom technique de la base dans le payload
            payload = {
                "username": st.session_state.username,
                "password": st.session_state.password,
                "db": st.session_state.database  # Nom technique de la base
            }
            
            response_database = st.session_state.session.post(
                url=login_url,
                json=payload
            )

            st.write(f"🔍 Debug: Code retour HTTP: {response_database.status_code}")
            if response_database.status_code != 200:
                st.write(f"🔍 Debug: Réponse brute: {response_database.text}")

            response_database.raise_for_status()

            user_data = response_database.json()

            if 'token' not in user_data:
                st.error("❌ Aucun token reçu après sélection de la base.")
                return False

            # Mettre à jour le token d'autorisation
            new_token = user_data['token']
            st.session_state.session.headers["Authorization"] = f"Bearer {new_token}"
            
            # CORRECTION: Ne pas effacer les cookies, ils peuvent être nécessaires
            # st.session_state.session.cookies.clear()

            st.success(f"✅ Connexion à la base « {db_name} » (DB: {st.session_state.database}) réussie.")
            return True

        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else "N/A"
            if status_code == 403:
                st.error("❌ Accès interdit à cette base. Vérifiez vos droits.")
                st.error("💡 Causes possibles:")
                st.error("• Votre compte n'a pas les droits d'accès à cette base")
                st.error("• Le nom technique de la base est incorrect")
                st.error("• Le token d'authentification a expiré")
            elif status_code == 404:
                st.error("❌ Base introuvable. Le nom technique est peut-être erroné.")
            elif status_code == 400:
                st.error("❌ Paramètres de requête invalides.")
                st.error("💡 Vérifiez que le nom technique de la base est correct.")
            else:
                st.error(f"❌ Erreur HTTP {status_code}: {e}")
            return False

        except requests.exceptions.RequestException as e:
            st.error(f"❌ Erreur réseau lors de la connexion à la base: {e}")
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
        

        st.write("🔍 Headers envoyés :")
        st.json(dict(st.session_state.session.headers))

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

    def run_diagnostic(self):
        st.subheader("🚨 Diagnostic complet API")

        # 1. Headers
        st.markdown("### 🔐 Headers actuels")
        st.json(dict(st.session_state.session.headers))

        # 2. Contexte utilisateur
        st.markdown("### 🌍 Contexte de session")
        st.write(f"- Utilisateur: {st.session_state.get('username', 'non défini')}")
        st.write(f"- Server URL suffix: `{st.session_state.get('urlserver')}`")
        st.write(f"- Base sélectionnée: `{st.session_state.get('database')}`")

        # 3. Authorization
        st.markdown("### 🛡️ Authorization Header")
        auth = st.session_state.session.headers.get("Authorization", "Aucun header Authorization trouvé.")
        st.code(auth)

        # 4. Bases disponibles
        st.markdown("### 📂 Bases disponibles (user_data['dbs'])")
        st.json(st.session_state.get("dbs", []))

        # 5. Endpoints API à tester
        st.markdown("### 🧪 Tests de connectivité API")
        base_url = f"https://isee{st.session_state.urlserver}.icareweb.com/apiv4/{st.session_state.database}"
        endpoints = [
            ("Infos de base", ""),
            ("Utilisateur courant", "/user"),
            ("Assets (1)", "/assets/?p=1&count=1"),
            ("Assets (10)", "/assets/?p=1&count=10"),
        ]

        for label, ep in endpoints:
            url = base_url + ep
            try:
                resp = st.session_state.session.get(url)
                code = resp.status_code
                preview = resp.text[:300].replace('\n', ' ')
                if code == 200:
                    st.success(f"{label} → ✅ 200 OK")
                elif code == 403:
                    st.error(f"{label} → ❌ 403 Forbidden")
                else:
                    st.warning(f"{label} → ⚠️ {code}")
                st.caption(f"`{url}` → Réponse : {preview}...")
            except Exception as e:
                st.error(f"{label} → Exception : {e}")

    def check_database_selection_method(self):
        """
        NOUVELLE MÉTHODE: Teste différentes approches pour la sélection de base
        """
        if not st.session_state.logged_in:
            st.warning("Vous devez d'abord vous connecter.")
            return
            
        st.subheader("🔬 Test des méthodes de sélection de base")
        
        # Méthode 1: GET avec URL modifiée (votre méthode actuelle - incorrecte)
        st.markdown("#### Méthode 1: GET sur /login/{database} (INCORRECTE)")
        if st.session_state.dbs:
            db_info = st.session_state.dbs[0]  # Prendre la première base
            test_url = f"https://isee{st.session_state.urlserver}.icareweb.com/apiv4/login/{db_info['db']}"
            try:
                resp = st.session_state.session.get(test_url)
                st.write(f"GET {test_url} → {resp.status_code}")
                st.write(f"Réponse: {resp.text[:200]}...")
            except Exception as e:
                st.error(f"Erreur: {e}")
        
        # Méthode 2: POST avec payload complet (CORRECTE)
        st.markdown("#### Méthode 2: POST sur /login/ avec payload complet (CORRECTE)")
        if st.session_state.dbs:
            db_info = st.session_state.dbs[0]
            login_url = f"https://isee{st.session_state.urlserver}.icareweb.com/apiv4/login/"
            payload = {
                "username": st.session_state.username,
                "password": st.session_state.password,
                "db": db_info['db']
            }
            try:
                resp = st.session_state.session.post(login_url, json=payload)
                st.write(f"POST {login_url} → {resp.status_code}")
                if resp.status_code == 200:
                    st.success("✅ Cette méthode fonctionne!")
                    data = resp.json()
                    if 'token' in data:
                        st.write("Token reçu avec succès")
                else:
                    st.write(f"Réponse: {resp.text[:200]}...")
            except Exception as e:
                st.error(f"Erreur: {e}")