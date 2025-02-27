from flask import Blueprint, redirect, request, url_for, session  # Importa le funzioni necessarie da Flask
import spotipy  # Libreria per interagire con l'API di Spotify
from spotipy.oauth2 import SpotifyOAuth  # Classe per la gestione dell'autenticazione con Spotify
from services.spotify_auth_service import SpotifyAuthService  # Importa il servizio di autenticazione personalizzato

# Credenziali dell'applicazione Spotify
SPOTIFY_CLIENT_ID = "d3c1badbe879439c85f4ee31bf30a33a"
SPOTIFY_CLIENT_SECRET = "12ccffe121454ab892ccd7890c4a8db1"
SPOTIFY_REDIRECT_URI = "https://5000-arbamarco-spotifyproget-zoymqvnn7wp.ws-eu118.gitpod.io/callback"
auth_bp = Blueprint('auth', __name__)

spotify_auth_service = SpotifyAuthService(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI)
# Crea un Blueprint per la gestione delle autenticazioni


@auth_bp.route('/')
def login():
    auth_url = spotify_auth_service.get_authorize_url()  
    return redirect(auth_url)

@auth_bp.route('/logout')
def logout():
    session.clear()  # Cancella l'access token salvato in sessione
    return redirect(url_for('auth.login'))


@auth_bp.route('/callback')
def callback():
    code = request.args.get('code')  # Ottiene il codice di autorizzazione dalla richiesta
    token_info = spotify_auth_service.get_access_token(code)  # Scambia il codice per un token di accesso
    session['token_info'] = token_info  # Salva il token nella sessione
    return redirect(url_for('home.homepage'))  # Reindirizza alla homepage dell'applicazione