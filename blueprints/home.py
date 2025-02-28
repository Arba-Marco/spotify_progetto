from flask import Blueprint, render_template, session, redirect, url_for, request
import spotipy
from spotipy.oauth2 import SpotifyOAuth

home_bp = Blueprint('home', __name__)

# Configurazione dell'autenticazione Spotify
sp_oauth = SpotifyOAuth(client_id='d3c1badbe879439c85f4ee31bf30a33a',
                         client_secret='12ccffe121454ab892ccd7890c4a8db1',
                         redirect_uri='https://5000-arbamarco-spotifyproget-zoymqvnn7wp.ws-eu118.gitpod.io/callback',
                         scope='user-library-read',
                         show_dialog=True)

def get_spotify_client():
    """Restituisce un client Spotify autenticato oppure None se l'utente non è loggato."""
    token_info = session.get('token_info')
    if token_info:
        return spotipy.Spotify(auth=token_info['access_token'])
    return None

@home_bp.route('/home', methods=['GET', 'POST'])
def homepage():
    """Gestisce la homepage con la ricerca di playlist."""
    sp = get_spotify_client()
    user_info = None
    playlists = []

    if sp:
        try:
            user_info = sp.current_user()
            playlists = sp.current_user_playlists()['items']
        except Exception as e:
            print("Errore nell'accesso Spotify:", e)
    else:
        # Mostriamo playlist pubbliche generiche se non loggato
        sp_public = spotipy.Spotify()
        playlists = sp_public.search(q='top playlists', type='playlist', limit=10)['playlists']['items']
    
    search_results = []
    if request.method == 'POST':
        query = request.form.get('search_query')
        if query:
            search_results = search_spotify(query)
    
    return render_template('home.html', user_info=user_info, playlists=playlists, search_results=search_results)

@home_bp.route('/search_playlist', methods=['POST'])
def search_playlist():
    """Gestisce la ricerca delle playlist."""
    query = request.form.get('search_query')
    search_results = []
    if query:
        search_results = search_spotify(query)
    return render_template('home.html', search_results=search_results)

@home_bp.route('/playlist_tracks/<playlist_id>')
def playlist_tracks(playlist_id):
    """Mostra i brani di una playlist specifica."""
    sp = get_spotify_client()
    tracks = []

    if sp:
        try:
            tracks = sp.playlist_tracks(playlist_id)['items']
        except Exception as e:
            print("Errore nel recupero delle tracce:", e)

    return render_template('playlist_tracks.html', tracks=tracks)

def search_spotify(query):
    """Effettua una ricerca di playlist su Spotify."""
    sp = spotipy.Spotify(auth_manager=sp_oauth)
    result = sp.search(q=query, type='playlist', limit=10)
    return result['playlists']['items']