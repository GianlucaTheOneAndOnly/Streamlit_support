import streamlit as st
import time
from datetime import datetime, timedelta


# --- STYLE LOGIN SIMPLE ---
LOGIN_STYLE = """
<style>
    .login-container {
        max-width: 400px;
        margin: 2rem auto;
        padding: 2rem;
        border: 1px solid #ddd;
        border-radius: 8px;
        background-color: #f9f9f9;
    }
    
    .login-title {
        text-align: center;
        color: #333;
        margin-bottom: 1.5rem;
    }
    
    .attempts-info {
        background-color: #e3f2fd;
        padding: 0.75rem;
        border-radius: 4px;
        margin-top: 1rem;
        font-size: 0.9rem;
        color: #1976d2;
    }
    
    .locked-warning {
        background-color: #ffebee;
        border: 1px solid #f44336;
        padding: 1rem;
        border-radius: 4px;
        margin-top: 1rem;
        color: #d32f2f;
    }
    
    /* Désactiver les raccourcis clavier problématiques */
    .stApp {
        -webkit-user-select: none;
        -moz-user-select: none;
        -ms-user-select: none;
        user-select: none;
    }
    
    .stTextInput input {
        -webkit-user-select: text !important;
        -moz-user-select: text !important;
        -ms-user-select: text !important;
        user-select: text !important;
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
            # st.rerun() supprimé car automatique dans un callback
        else:
            # Échec : incrémenter les tentatives (avec initialisation sécurisée)
            current_attempts = st.session_state.get("login_attempts", 0)
            st.session_state["login_attempts"] = current_attempts + 1
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
    
    # Container simple centré
    with st.container():
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        
        # Titre simple
        st.markdown('<h2 class="login-title">🔐 Connexion</h2>', unsafe_allow_html=True)
        
        # Vérifier le verrouillage
        is_locked, remaining_time = is_account_locked()
        
        if is_locked:
            # Affichage du verrouillage
            minutes = remaining_time // 60
            seconds = remaining_time % 60
            st.markdown(f'''
                <div class="locked-warning">
                    <strong>⏳ Compte temporairement verrouillé</strong><br>
                    Trop de tentatives incorrectes. Réessayez dans {minutes}m {seconds}s.
                </div>
            ''', unsafe_allow_html=True)
        else:
            # Interface de saisie normale - TEXTE VISIBLE
            st.text_input(
                "Mot de passe", 
                type="default",  # Changé à "default" pour voir le texte
                on_change=password_entered, 
                key="password",
                placeholder="Entrez votre mot de passe...",
                help="Le texte saisi est visible"
            )
            
            # Messages d'erreur simples
            attempts_remaining = get_attempts_remaining()
            
            if st.session_state.get("login_attempts", 0) > 0:
                if attempts_remaining > 0:
                    st.error(f"❌ Mot de passe incorrect. {attempts_remaining} tentative(s) restante(s).")
                else:
                    st.error("❌ Trop de tentatives. Compte verrouillé pour 5 minutes.")
            
            # Informations simples
            st.markdown(f'''
                <div class="attempts-info">
                    ℹ️ Tentatives: {st.session_state.get("login_attempts", 0)}/5
                </div>
            ''', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Auto-refresh pour le décompte du verrouillage (seulement si nécessaire)
    if is_locked and remaining_time > 0:
        time.sleep(1)
        st.rerun()  # Ici c'est OK car pas dans un callback
    
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