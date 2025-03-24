from flask import Blueprint, redirect, request, url_for, session, render_template
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Configurazione delle credenziali per l'autenticazione con Spotify
SPOTIFY_CLIENT_ID = "d3c1badbe879439c85f4ee31bf30a33a"
SPOTIFY_CLIENT_SECRET = "12ccffe121454ab892ccd7890c4a8db1"
SPOTIFY_REDIRECT_URI = "https://5000-arbamarco-spotifyproget-klqajfigswk.ws-eu118.gitpod.io/callback"

# Blueprint per l'autenticazione
auth_bp = Blueprint('auth', __name__)

# Configurazione dell'autenticazione Spotify
sp_oauth = SpotifyOAuth(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET,
    redirect_uri=SPOTIFY_REDIRECT_URI,
    scope='playlist-modify-public playlist-modify-private user-library-read user-read-private'
)

def get_token():
    """Recupera il token aggiornato o lo aggiorna se è scaduto."""
    token_info = session.get('token_info', None)

    if not token_info:
        return None  # Nessun token disponibile

    # Controlla se il token è scaduto e lo aggiorna
    if sp_oauth.is_token_expired(token_info):
        token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
        session['token_info'] = token_info  # Aggiorna il token nella sessione

    return token_info['access_token']

@auth_bp.route('/')
def login():
    """Mostra la homepage senza alcun utente loggato."""
    session.clear()  # Cancella ogni sessione attiva all'avvio
    return render_template('home.html', user_info=None, playlists=[])

@auth_bp.route('/login_spotify')
def login_spotify():
    """Reindirizza alla pagina di login di Spotify forzando sempre il login."""
    auth_url = sp_oauth.get_authorize_url() + "&show_dialog=true"  # Forza il login ogni volta
    return redirect(auth_url)

@auth_bp.route('/callback')
def callback():
    """Gestisce la risposta di Spotify dopo il login."""
    code = request.args.get('code')
    error = request.args.get('error')

    if error == "access_denied" or not code:
        return redirect(url_for('auth.login'))  # Se c'è un errore o l'utente annulla il login, torna alla homepage

    # Recupera il token di accesso di Spotify
    token_info = sp_oauth.get_access_token(code)
    session['token_info'] = token_info  # Salva il token nella sessione per uso futuro

    # Recupera le informazioni dell'utente
    sp = spotipy.Spotify(auth=token_info['access_token'])
    session['user_info'] = sp.current_user()

    return redirect(url_for('home.homepage'))  # Dopo il login, reindirizza alla homepage

@auth_bp.route('/logout')
def logout():
    """Logout solo da Spotify e rimuove immediatamente i messaggi flash."""
    session.pop('token_info', None)  # Rimuove solo il token di Spotify
    session.pop('_flashes', None)  # Cancella immediatamente i messaggi flash
    return redirect(url_for('auth.login'))  # Torna alla login

@auth_bp.route('/profile')
def profile():
    """Mostra il profilo utente con token aggiornato."""
    access_token = get_token()
    if not access_token:
        return redirect(url_for('auth.login_spotify'))  # Richiede il login se non c'è un token valido

    sp = spotipy.Spotify(auth=access_token)
    user_info = sp.current_user()

    return render_template('profile.html', user_info=user_info)