from flask import Blueprint, redirect, request, url_for, session, render_template
import spotipy
from spotipy.oauth2 import SpotifyOAuth

SPOTIFY_CLIENT_ID = "d3c1badbe879439c85f4ee31bf30a33a"
SPOTIFY_CLIENT_SECRET = "12ccffe121454ab892ccd7890c4a8db1"
SPOTIFY_REDIRECT_URI = "https://5000-arbamarco-spotifyproget-zoymqvnn7wp.ws-eu118.gitpod.io/callback"

auth_bp = Blueprint('auth', __name__)

# Configurazione dell'autenticazione Spotify
sp_oauth = SpotifyOAuth(client_id=SPOTIFY_CLIENT_ID,
                         client_secret=SPOTIFY_CLIENT_SECRET,
                         redirect_uri=SPOTIFY_REDIRECT_URI,
                         scope='user-library-read')

@auth_bp.route('/')
def login():
    """Mostra la homepage senza alcun utente loggato."""
    session.clear()  # Cancella ogni sessione attiva all'avvio
    return render_template('home.html', user_info=None, playlists=[])

@auth_bp.route('/login_spotify')
def login_spotify():
    """Reindirizza alla pagina di login di Spotify forzando sempre il login."""
    auth_url = sp_oauth.get_authorize_url()
    auth_url += "&show_dialog=true"  # <-- Aggiunge il parametro manualmente
    return redirect(auth_url)

@auth_bp.route('/callback')
def callback():
    """Gestisce la risposta di Spotify dopo il login."""
    code = request.args.get('code')
    error = request.args.get('error')  # Spotify passa 'access_denied' se l'utente annulla

    if error == "access_denied" or not code:
        # Se l'utente annulla il login, lo reindirizziamo alla homepage senza loggarlo
        return redirect(url_for('home.homepage'))

    # Se il login ha successo, otteniamo il token e salviamo la sessione
    token_info = sp_oauth.get_access_token(code)
    session['token_info'] = token_info
    return redirect(url_for('home.homepage'))

@auth_bp.route('/logout')
def logout():
    """Elimina la sessione e ricarica la homepage senza alcun utente loggato."""
    session.clear()
    return redirect(url_for('auth.login'))  # Torna alla homepage con utente disconnesso
