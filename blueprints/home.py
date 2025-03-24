from flask import Blueprint, render_template, request, session, flash, redirect, url_for
import spotipy
from spotipy.oauth2 import SpotifyOAuth, SpotifyClientCredentials
from flask_login import current_user
from services.db import get_db

home_bp = Blueprint('home', __name__)

# Configurazione dell'autenticazione Spotify
SPOTIFY_CLIENT_ID = 'd3c1badbe879439c85f4ee31bf30a33a'
SPOTIFY_CLIENT_SECRET = '12ccffe121454ab892ccd7890c4a8db1'
SPOTIFY_REDIRECT_URI = 'https://5000-arbamarco-spotifyproget-klqajfigswk.ws-eu118.gitpod.io/callback'

sp_oauth = SpotifyOAuth(client_id=SPOTIFY_CLIENT_ID,
                         client_secret=SPOTIFY_CLIENT_SECRET,
                         redirect_uri=SPOTIFY_REDIRECT_URI,
                         scope='user-library-read user-read-private',
                         show_dialog=True)

# Client pubblico per utenti non autenticati
client_credentials_manager = SpotifyClientCredentials(client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET)
sp_public = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

def get_spotify_client():
    """Restituisce un client Spotify autenticato oppure un client pubblico se l'utente non è loggato."""
    token_info = session.get('token_info')
    if token_info:
        return spotipy.Spotify(auth=token_info['access_token'])
    return sp_public  # Client pubblico se non autenticato

@home_bp.route('/home', methods=['GET', 'POST'])
def homepage():
    """Gestisce la homepage con la ricerca di playlist."""
    sp = get_spotify_client()
    user_info = None
    playlists = []

    if token_info := session.get('token_info'):
        try:
            sp = spotipy.Spotify(auth=token_info['access_token'])
            user_info = sp.current_user()
            playlists = sp.current_user_playlists()['items']
        except Exception as e:
            print("Errore nell'accesso Spotify:", e)
    else:
        # Mostriamo playlist pubbliche generiche se non loggato
        playlists = sp_public.search(q='top playlists', type='playlist', limit=10)['playlists']['items']
    
    search_results = []
    if request.method == 'POST':
        query = request.form.get('search_query')
        if query:
            search_results = search_spotify(query)
    
    return render_template('home.html', user_info=user_info, playlists=playlists, search_results=search_results)

@home_bp.route('/search_playlist', methods=['POST', 'GET'])
def search_playlist():
    """Effettua la ricerca di playlist su Spotify, sia per utenti loggati che non loggati."""
    sp = get_spotify_client()
    search_results = []

    if request.method == 'POST':
        query = request.form.get('search_query')
        if query:
            try:
                print(f"Eseguendo la ricerca per: {query}")
                search_results = sp.search(q=query, type='playlist', limit=10)['playlists']['items']
            except Exception as e:
                print("Errore nella ricerca delle playlist:", e)
    
    return render_template('home.html', search_results=search_results, user_info=session.get('user_info'), playlists=session.get('playlists', []))




@home_bp.route('/playlist_tracks/<playlist_id>')
def playlist_tracks(playlist_id):
    """Mostra i brani di una playlist specifica anche se l'utente non è loggato."""
    sp = get_spotify_client()
    tracks = []

    try:
        tracks = sp.playlist_tracks(playlist_id)['items']
    except Exception as e:
        print("Errore nel recupero delle tracce:", e)

    return render_template('playlist_tracks.html', tracks=tracks)

@home_bp.route('/add_to_favorites', methods=['POST'])
def add_to_favorites():
    """Salva una playlist tra i preferiti nella sessione Flask."""
    playlist_id = request.form.get('playlist_id')
    playlist_name = request.form.get('playlist_name')

    if 'favorite_playlists' not in session:
        session['favorite_playlists'] = []

    favorite_playlists = session['favorite_playlists']

    # Aggiungi solo se non è già nei preferiti
    if not any(p['id'] == playlist_id for p in favorite_playlists):
        favorite_playlists.append({'id': playlist_id, 'name': playlist_name})

    session['favorite_playlists'] = favorite_playlists
    return redirect(url_for('home.view_favorites'))

@home_bp.route('/save_playlist/<playlist_id>')
def save_playlist(playlist_id):
    """Salva una playlist nel database per utenti loggati, o nella sessione per ospiti."""
    playlist_name = request.args.get('playlist_name', '')  # Passa il nome della playlist come parametro opzionale

    if current_user.is_authenticated:
        try:
            conn = get_db()
            with conn.cursor() as cursor:
                cursor.execute('''
                    INSERT INTO saved_playlists (user_id, playlist_id, playlist_name)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE playlist_name = VALUES(playlist_name)
                ''', (current_user.id, playlist_id, playlist_name))
                conn.commit()
            conn.close()
            flash("Playlist salvata nel tuo profilo!", "success")
        except Exception as e:
            flash(f"Errore nel salvataggio: {e}", "danger")
    else:
        if 'saved_playlists' not in session:
            session['saved_playlists'] = []
        if playlist_id not in session['saved_playlists']:
            session['saved_playlists'].append(playlist_id)
            session.modified = True
            flash("Playlist salvata temporaneamente. Effettua il login per salvarla permanentemente.", "info")

    return redirect(url_for('home.view_saved_playlists'))


@home_bp.route('/saved_playlists')
def view_saved_playlists():
    """Mostra le playlist salvate (dal database per utenti loggati o dalla sessione per ospiti)."""
    sp = get_spotify_client()
    playlists = []

    if current_user.is_authenticated:
        try:
            conn = get_db()
            with conn.cursor() as cursor:
                cursor.execute('SELECT playlist_id FROM saved_playlists WHERE user_id = %s', (current_user.id,))
                rows = cursor.fetchall()
            conn.close()
            playlist_ids = [row['playlist_id'] for row in rows]
        except Exception as e:
            flash(f"Errore nel recupero delle playlist salvate: {e}", "danger")
            playlist_ids = []
    else:
        playlist_ids = session.get('saved_playlists', [])

    # Recupera dettagli playlist da Spotify
    for pid in playlist_ids:
        try:
            playlists.append(sp.playlist(pid))
        except Exception as e:
            print(f"Errore nel recupero della playlist {pid}: {e}")

    return render_template('saved_playlists.html', playlists=playlists)

@home_bp.route('/favorites')
def view_favorites():
    """Mostra le playlist preferite salvate nella sessione."""
    favorite_playlists = session.get('favorite_playlists', [])
    return render_template('favorites.html', favorite_playlists=favorite_playlists)

@home_bp.route('/remove_from_favorites/<playlist_id>')
def remove_from_favorites(playlist_id):
    """Rimuove una playlist dai preferiti."""
    favorite_playlists = session.get('favorite_playlists', [])
    session['favorite_playlists'] = [p for p in favorite_playlists if p['id'] != playlist_id]
    return redirect(url_for('home.view_favorites'))
