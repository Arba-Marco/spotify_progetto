from flask import Blueprint, redirect, request, url_for, session
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from services.spotify_auth_service import SpotifyAuthService

SPOTIFY_CLIENT_ID = "d3c1badbe879439c85f4ee31bf30a33a"
SPOTIFY_CLIENT_SECRET = "12ccffe121454ab892ccd7890c4a8db1"
SPOTIFY_REDIRECT_URI = "https://5000-arbamarco-spotifyproget-zoymqvnn7wp.ws-eu118.gitpod.io/callback"
auth_bp = Blueprint('auth', __name__)

spotify_auth_service = SpotifyAuthService(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI)



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
    code = request.args.get('code')
    token_info = spotify_auth_service.get_access_token(code)  
    session['token_info'] = token_info
    return redirect(url_for('home.homepage'))