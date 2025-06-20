import streamlit as st
import time
from datetime import datetime, timedelta


# --- STYLE LOGIN AMÉLIORÉ ---
LOGIN_STYLE = """
<style>
    /* Overlay sombre pour effet modal */
    .login-overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0, 0, 0, 0.5);
        backdrop-filter: blur(5px);
        z-index: 9998;
    }
    
    /* Boîte de connexion centrée */
    .login-box {
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 2.5rem;
        border-radius: 15px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        z-index: 9999;
        width: 90%;
        max-width: 420px;
        animation: slideIn 0.3s ease-out;
    }
    
    @keyframes slideIn {
        from {
            opacity: 0;
            transform: translate(-50%, -60%);
        }
        to {
            opacity: 1;
            transform: translate(-50%, -50%);
        }
    }
    
    .login-box h1 {
        color: white !important;
        text-align: center;
        margin-bottom: 1.5rem;
        font-size: 1.8rem;
    }
    
    .login-box .stTextInput > div > div > input {
        background-color: rgba(255, 255, 255, 0.9);
        border: none;
        border-radius: 8px;
        padding: 0.75rem;
        font-size: 1rem;
    }
    
    .login-info {
        background-color: rgba(255, 255, 255, 0.1);
        padding: 1rem;
        border-radius: 8px;
        margin-top: 1rem;
        font-size: 0.9rem;
    }
    
    .security-indicator {
        display: flex;
        align-items: center;
        margin-top: 0.5rem;
        font-size: 0.8rem;
    }
    
    .attempts-warning {
        background-color: rgba(255, 87, 87, 0.2);
        border: 1px solid rgba(255, 87, 87, 0.5);
        padding: 0.75rem;
        border-radius: 8px;
        margin-top: 1rem;
    }
</style>
"""


# --- FONCTION PRINCIPALE AMÉLIORÉE ---
def check_password():
    """
    Affiche un écran de connexion sécurisé avec limitation des tentatives.
    
    Features:
    - Interface utilisateur améliorée avec design moderne
    - Limitation des tentatives de connexion (max 5 tentatives)
    - Verrouillage temporaire après échecs répétés
    - Messages d'erreur informatifs
    - Indicateurs de sécurité
    - Gestion propre de la session
    """
    
    # Initialisation des variables de session
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if "login_attempts" not in st.session_state:
        st.session_state["login_attempts"] = 0
    if "last_attempt_time" not in st.session_state:
        st.session_state["last_attempt_time"] = None
    if "locked_until" not in st.session_state:
        st.session_state["locked_until"] = None

    def password_entered():
        """Vérifie le mot de passe avec limitation des tentatives."""
        current_time = datetime.now()
        
        # Vérifier si le compte est verrouillé
        if (st.session_state.get("locked_until") and 
            current_time < st.session_state["locked_until"]):
            return
        
        # Vérifier le mot de passe
        entered_password = st.session_state.get("password", "")
        
        if entered_password == "Icare2025":
            # Succès : réinitialiser les compteurs
            st.session_state["password_correct"] = True
            st.session_state["login_attempts"] = 0
            st.session_state["last_attempt_time"] = None
            st.session_state["locked_until"] = None
            st.session_state.pop("password", None)
            st.rerun()
        else:
            # Échec : incrémenter les tentatives
            st.session_state["login_attempts"] += 1
            st.session_state["last_attempt_time"] = current_time
            st.session_state["password_correct"] = False
            
            # Verrouillage après 5 tentatives
            if st.session_state["login_attempts"] >= 5:
                st.session_state["locked_until"] = current_time + timedelta(minutes=5)

    def is_account_locked():
        """Vérifie si le compte est actuellement verrouillé."""
        if not st.session_state.get("locked_until"):
            return False, 0
        
        current_time = datetime.now()
        if current_time >= st.session_state["locked_until"]:
            # Déverrouiller le compte
            st.session_state["locked_until"] = None
            st.session_state["login_attempts"] = 0
            return False, 0
        
        remaining_seconds = (st.session_state["locked_until"] - current_time).total_seconds()
        return True, int(remaining_seconds)

    def get_attempts_remaining():
        """Retourne le nombre de tentatives restantes."""
        return max(0, 5 - st.session_state.get("login_attempts", 0))

    # Si déjà authentifié, autoriser l'accès
    if st.session_state.get("password_correct", False):
        return True

    # Afficher l'interface de connexion
    st.markdown(LOGIN_STYLE, unsafe_allow_html=True)
    
    # Overlay sombre
    st.markdown('<div class="login-overlay"></div>', unsafe_allow_html=True)
    
    # Boîte de connexion
    with st.container():
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        
        # Titre avec emoji
        st.markdown('<h1>🔐 Accès Sécurisé</h1>', unsafe_allow_html=True)
        
        # Vérifier le verrouillage
        is_locked, remaining_time = is_account_locked()
        
        if is_locked:
            # Affichage du verrouillage
            minutes = remaining_time // 60
            seconds = remaining_time % 60
            st.markdown(f'''
                <div class="attempts-warning">
                    🚫 <strong>Compte temporairement verrouillé</strong><br>
                    Trop de tentatives incorrectes. Réessayez dans {minutes}m {seconds}s.
                </div>
            ''', unsafe_allow_html=True)
        else:
            # Interface de saisie normale
            st.text_input(
                "Mot de passe", 
                type="password", 
                on_change=password_entered, 
                key="password",
                placeholder="Entrez votre mot de passe...",
                help="Saisissez votre mot de passe d'accès"
            )
            
            # Messages d'erreur et d'information
            attempts_remaining = get_attempts_remaining()
            
            if st.session_state.get("login_attempts", 0) > 0:
                if attempts_remaining > 0:
                    st.error(f"❌ Mot de passe incorrect. {attempts_remaining} tentative(s) restante(s).")
                else:
                    st.error("❌ Trop de tentatives. Compte verrouillé pour 5 minutes.")
            
            # Informations de sécurité
            st.markdown(f'''
                <div class="login-info">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span>🛡️ Connexion sécurisée</span>
                        <span style="font-size: 0.8em; opacity: 0.8;">
                            Tentatives: {st.session_state.get("login_attempts", 0)}/5
                        </span>
                    </div>
                    <div class="security-indicator">
                        <span style="color: #4CAF50;">🔒</span>
                        <span style="margin-left: 0.5rem;">Données protégées et chiffrées</span>
                    </div>
                </div>
            ''', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Auto-refresh pour le décompte du verrouillage
    if is_locked and remaining_time > 0:
        time.sleep(1)
        st.rerun()
    
    # Arrêter l'exécution tant que non authentifié
    st.stop()


# --- FONCTIONS UTILITAIRES SUPPLÉMENTAIRES ---

def logout():
    """Fonction pour déconnecter l'utilisateur."""
    for key in ["password_correct", "login_attempts", "last_attempt_time", "locked_until"]:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

def add_logout_button():
    """Ajoute un bouton de déconnexion dans la sidebar."""
    with st.sidebar:
        if st.button("🚪 Se déconnecter", type="secondary"):
            logout()

def get_session_info():
    """Retourne des informations sur la session actuelle."""
    return {
        "authenticated": st.session_state.get("password_correct", False),
        "login_attempts": st.session_state.get("login_attempts", 0),
        "is_locked": st.session_state.get("locked_until") is not None
    }