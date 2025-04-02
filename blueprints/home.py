from flask import Blueprint, render_template, request, session, flash, redirect, url_for
import spotipy
from spotipy.oauth2 import SpotifyOAuth, SpotifyClientCredentials
from flask_login import current_user
from services.db import get_db
import pandas as pd
import plotly.express as px

home_bp = Blueprint('home', __name__)

# Configurazione dell'autenticazione Spotify
SPOTIFY_CLIENT_ID = 'd3c1badbe879439c85f4ee31bf30a33a'
SPOTIFY_CLIENT_SECRET = '12ccffe121454ab892ccd7890c4a8db1'
SPOTIFY_REDIRECT_URI = 'https://5000-arbamarco-spotifyproget-pz7ajcg4azc.ws-eu118.gitpod.io/callback'

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

    # Verifica se l'utente è loggato su Spotify (controllo tramite il token in sessione)
    if token_info := session.get('token_info'):
        try:
            sp = spotipy.Spotify(auth=token_info['access_token'])
            user_info = sp.current_user()  # Se l'utente è loggato, ottieni le informazioni
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



@home_bp.route('/playlist_analysis')
def playlist_analysis():
    """Visualizza l'analisi delle playlist (top artisti, top album, distribuzione dei generi)."""
    sp = get_spotify_client()
    
    try:
        tracks_data = []
        
        # Recupera playlist pubbliche anziché quelle dell'utente
        playlists = sp.search(q='top playlists', type='playlist', limit=5).get('playlists', {}).get('items', [])
        
        for playlist in playlists:
            playlist_id = playlist.get('id')
            if not playlist_id:
                continue  # Se manca l'ID della playlist, salta

            tracks_response = sp.playlist_tracks(playlist_id)
            tracks = tracks_response.get('items', []) if tracks_response else []

            for track in tracks:
                if not track or 'track' not in track or track['track'] is None:
                    continue  # Salta tracce non valide

                track_data = {
                    'track_name': track['track'].get('name', 'Sconosciuto'),
                    'artist_name': track['track']['artists'][0].get('name', 'Sconosciuto') if track['track'].get('artists') else 'Sconosciuto',
                    'album_name': track['track']['album'].get('name', 'Sconosciuto') if track['track'].get('album') else 'Sconosciuto',
                    'genre': track['track']['album'].get('genres', ['Unknown'])[0] if track['track'].get('album') else 'Unknown'
                }
                tracks_data.append(track_data)

        # Se non ci sono dati, mostra un messaggio di errore
        if not tracks_data:
            flash("Nessuna traccia trovata nelle playlist pubbliche.", "warning")
            return redirect(url_for('home.homepage'))

        # Converti i dati in un DataFrame pandas
        df = pd.DataFrame(tracks_data)

        # Analisi: Top 5 artisti
        top_artists = df['artist_name'].value_counts().head(5)

        # Analisi: Top 5 album
        top_albums = df['album_name'].value_counts().head(5)

        # Analisi: Distribuzione dei generi musicali
        genre_distribution = df['genre'].value_counts()

        # Crea grafici per le analisi
        artist_fig = px.bar(top_artists, x=top_artists.index, y=top_artists.values, labels={'x': 'Artista', 'y': 'Numero di brani'})
        album_fig = px.bar(top_albums, x=top_albums.index, y=top_albums.values, labels={'x': 'Album', 'y': 'Numero di brani'})
        genre_fig = px.pie(genre_distribution, names=genre_distribution.index, values=genre_distribution.values, title='Distribuzione dei generi musicali')

        return render_template('playlist_analysis.html', artist_fig=artist_fig.to_html(), album_fig=album_fig.to_html(), genre_fig=genre_fig.to_html())
    
    except Exception as e:
        flash(f"Errore durante l'analisi delle playlist: {e}", "danger")
        return redirect(url_for('home.homepage'))



@home_bp.route('/spotify_playlists')
def view_spotify_playlists():
    if 'token_info' not in session:
        flash("Devi collegarti a Spotify per vedere le tue playlist.", "warning")
        return redirect(url_for('home.homepage'))

    sp = spotipy.Spotify(auth=session['token_info']['access_token'])
    try:
        playlists = sp.current_user_playlists()['items']
        user_info = sp.current_user()  # Recupera le informazioni utente da Spotify
    except Exception as e:
        flash(f"Errore nel recupero delle playlist: {e}", "danger")
        return redirect(url_for('home.homepage'))

    return render_template('spotify_playlists.html', playlists=playlists, user_info=user_info)


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

    # Recupera dettagli playlist da SPOTIFI
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
