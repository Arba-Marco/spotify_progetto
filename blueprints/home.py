from flask import Blueprint, render_template, request, session, flash, redirect, url_for
import spotipy
from spotipy.oauth2 import SpotifyOAuth, SpotifyClientCredentials
from flask_login import current_user
from services.db import get_db
import pandas as pd
import plotly.express as px
import pymysql
import os
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

home_bp = Blueprint('home', __name__)

# Configurazione dell'autenticazione Spotify
SPOTIFY_CLIENT_ID = 'd3c1badbe879439c85f4ee31bf30a33a'
SPOTIFY_CLIENT_SECRET = '12ccffe121454ab892ccd7890c4a8db1'
SPOTIFY_REDIRECT_URI = 'https://5000-arbamarco-spotifyproget-pz7ajcg4azc.ws-eu118.gitpod.io/callback'

sp_oauth = SpotifyOAuth(client_id=SPOTIFY_CLIENT_ID,
                        client_secret=SPOTIFY_CLIENT_SECRET,
                        redirect_uri=SPOTIFY_REDIRECT_URI,
                        scope='user-library-read user-read-private playlist-modify-public playlist-modify-private',
                        show_dialog=True)

# Client pubblico per utenti non autenticati
client_credentials_manager = SpotifyClientCredentials(client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET)
sp_public = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

def view_saved_playlists():
    """Mostra le playlist salvate (dal database per utenti loggati o dalla sessione per ospiti)."""
    sp = get_spotify_client()
    playlists = []

    if current_user.is_authenticated:
        print("Utente autenticato. Recupero playlist dal database.")
        try:
            conn = get_db()
            with conn.cursor() as cursor:
                print(f"Esecuzione della query: SELECT playlist_id FROM saved_playlists WHERE user_id = {current_user.id}")
                cursor.execute('SELECT playlist_id FROM saved_playlists WHERE user_id = %s', (current_user.id,))
                rows = cursor.fetchall()
                print(f"Risultati della query: {rows}")
                playlist_ids = [row['playlist_id'] for row in rows]
            conn.close()
        except Exception as e:
            print(f"Errore nel recupero delle playlist salvate: {e}")
            flash(f"Errore nel recupero delle playlist salvate: {e}", "danger")
            playlist_ids = []
    else:
        print("Utente non autenticato. Recupero playlist dalla sessione.")
        playlist_ids = session.get('saved_playlists', [])

    # Recupera dettagli playlist da SPOTIFY
    for pid in playlist_ids:
        try:
            playlist_data = sp.playlist(pid)
            playlists.append({
                'id': pid,
                'name': playlist_data.get('name', 'Playlist senza nome'),
                'images': playlist_data.get('images', []),
                'owner': playlist_data.get('owner', {}).get('display_name', 'Unknown')
            })
        except Exception as e:
            print(f"Errore nel recupero della playlist {pid}: {e}")
            # Add basic info even if Spotify API fails
            playlists.append({
                'id': pid,
                'name': 'Playlist non disponibile',
                'images': [],
                'owner': 'Unknown'
            })

    return render_template('saved_playlists.html', playlists=playlists)

def get_db():
    try:
        conn = pymysql.connect(
            host=os.environ.get("MYSQL_HOST", "localhost"),
            user=os.environ.get("MYSQL_USER", "root"),
            password=os.environ.get("MYSQL_PASSWORD", "password"),
            database=os.environ.get("MYSQL_DATABASE", "spotify"),
            cursorclass=pymysql.cursors.DictCursor
        )
        return conn
    except pymysql.MySQLError as e:
        print(f"Errore di connessione al database: {e}")
        raise e

def get_spotify_client():
    token_info = session.get('token_info')
    if token_info:
        return spotipy.Spotify(auth=token_info['access_token'])
    return sp_public

def fetch_playlist_data(sp, playlist_id, artist_genres):
    try:
        results = sp.playlist_tracks(playlist_id)
        tracks = results.get('items', [])
        while results.get('next'):
            results = sp.next(results)
            tracks.extend(results.get('items', []))

        playlist_info = sp.playlist(playlist_id)
        playlist_name = playlist_info.get('name', 'Playlist senza nome')

        track_set = set()
        artist_set = set()
        popularity = []
        genre_count = defaultdict(int)
        year_count = defaultdict(int)

        for track in tracks:
            if not track or 'track' not in track or track['track'] is None:
                continue

            track_info = track['track']
            track_set.add(track_info.get('name', 'Sconosciuto'))
            
            artist_info = track_info.get('artists', [{}])[0]
            artist_name = artist_info.get('name', 'Sconosciuto')
            artist_set.add(artist_name)

            popularity.append(track_info.get('popularity', 0))

            artist_id = artist_info.get('id')
            if artist_id and artist_id not in artist_genres:
                try:
                    artist_data = sp.artist(artist_id)
                    genres = artist_data.get('genres', [])
                    artist_genres[artist_id] = genres[0] if genres else 'Unknown'
                except Exception as e:
                    print(f"Errore nel recupero del genere per l'artista {artist_id}: {e}")
                    artist_genres[artist_id] = 'Unknown'

            genre = artist_genres.get(artist_id, 'Unknown')
            genre_count[genre] += 1

            release_year = track_info.get('album', {}).get('release_date', '').split('-')[0] if track_info.get('album', {}).get('release_date') else None
            if release_year:
                year_count[release_year] += 1

        return {
            'playlist': {
                'name': playlist_name,
                'tracks': list(track_set),
                'artists': list(artist_set),
                'popularity': popularity,
                'genres': genre_count,
                'years': year_count
            },
            'track_set': track_set,
            'artist_set': artist_set,
            'popularity': popularity,
            'genre_count': genre_count,
            'year_count': year_count
        }

    except Exception as e:
        print(f"Errore nel recupero dati playlist {playlist_id}: {e}")
        return None


def get_playlist_data(sp, playlist_id):
    try:
        tracks_response = sp.playlist_tracks(playlist_id, limit=100)  # Limita il numero di tracce
        tracks = tracks_response.get('items', []) if tracks_response else []

        tracks_data = []
        for track in tracks:
            if not track or 'track' not in track or track['track'] is None:
                continue

            track_info = track['track']
            artist_info = track_info.get('artists', [{}])[0]
            artist_id = artist_info.get('id')
            genre = 'Unknown'

            if artist_id:
                try:
                    artist_data = sp.artist(artist_id)
                    genres = artist_data.get('genres', [])
                    genre = genres[0] if genres else 'Unknown'
                except Exception as e:
                    print(f"Errore nel recupero genere artista {artist_id}: {e}")

            track_data = {
                'track_id': track_info.get('id'),
                'track_name': track_info.get('name', 'Sconosciuto'),
                'artist_name': artist_info.get('name', 'Sconosciuto'),
                'artist_id': artist_id,
                'album_name': track_info.get('album', {}).get('name', 'Sconosciuto'),
                'genre': genre,
                'popularity': track_info.get('popularity', 0),
                'duration_ms': track_info.get('duration_ms', 0)
            }
            tracks_data.append(track_data)

        return {
            'id': playlist_id,
            'name': sp.playlist(playlist_id).get('name', 'Playlist senza nome'),
            'tracks': tracks_data,
            'total_tracks': len(tracks_data)
        }

    except Exception as e:
        print(f"Errore nel recupero dati playlist {playlist_id}: {e}")
        return None
    """Recupera e struttura i dati di una playlist."""
    tracks_data = []
    try:
        tracks_response = sp.playlist_tracks(playlist_id)
        tracks = tracks_response.get('items', []) if tracks_response else []

        for track in tracks:
            if not track or 'track' not in track or track['track'] is None:
                continue

            track_info = track['track']
            artist_info = track_info.get('artists', [{}])[0]
            artist_id = artist_info.get('id')
            genre = 'Unknown'

            if artist_id:
                try:
                    artist_data = sp.artist(artist_id)
                    genres = artist_data.get('genres', [])
                    genre = genres[0] if genres else 'Unknown'
                except Exception as e:
                    print(f"Errore nel recupero genere artista {artist_id}: {e}")

            track_data = {
                'track_id': track_info.get('id'),
                'track_name': track_info.get('name', 'Sconosciuto'),
                'artist_name': artist_info.get('name', 'Sconosciuto'),
                'artist_id': artist_id,
                'album_name': track_info.get('album', {}).get('name', 'Sconosciuto'),
                'genre': genre,
                'popularity': track_info.get('popularity', 0),
                'duration_ms': track_info.get('duration_ms', 0)
            }
            tracks_data.append(track_data)
            
        # Aggiungi informazioni sulla playlist
        playlist_info = sp.playlist(playlist_id)
        return {
            'id': playlist_id,
            'name': playlist_info.get('name', 'Playlist senza nome'),
            'tracks': tracks_data,
            'total_tracks': len(tracks_data)
        }
        
    except Exception as e:
        print(f"Errore nel recupero dati playlist {playlist_id}: {e}")
        return None


@home_bp.route('/recommendations', methods=['GET', 'POST'])
def get_recommendations():
    """Ottiene suggerimenti musicali basati su input dell'utente"""
    sp = get_spotify_client()
    
    if request.method == 'POST':
        # Recupera i parametri dal form
        seed_artists = request.form.get('seed_artists', '').split(',')
        seed_tracks = request.form.get('seed_tracks', '').split(',')
        seed_genres = request.form.get('seed_genres', '').split(',')
        
        # Filtra i valori vuoti
        seed_artists = [a.strip() for a in seed_artists if a.strip()]
        seed_tracks = [t.strip() for t in seed_tracks if t.strip()]
        seed_genres = [g.strip() for g in seed_genres if g.strip()]
        
        try:
            # Ottieni le raccomandazioni
            recommendations = sp.recommendations(
                seed_artists=seed_artists[:5],  # Spotify accetta max 5 seed
                seed_tracks=seed_tracks[:5],
                seed_genres=seed_genres[:5],
                limit=20
            )
            
            # Se l'utente è autenticato, recupera le sue playlist
            user_playlists = []
            if 'token_info' in session:
                user_playlists = sp.current_user_playlists(limit=50)['items']
            
            return render_template('recommendations.html', 
                                tracks=recommendations['tracks'],
                                user_playlists=user_playlists,
                                seeds={'artists': seed_artists, 
                                      'tracks': seed_tracks, 
                                      'genres': seed_genres})
            
        except Exception as e:
            flash(f"Errore nel recuperare i suggerimenti: {str(e)}", "danger")
            return redirect(url_for('home.get_recommendations'))
    
    # Se è una richiesta GET, mostra il form di ricerca
    return render_template('recommendations_form.html')



@home_bp.route('/share_playlist/<playlist_id>')
def share_playlist(playlist_id):
    """Genera un link condivisibile per la playlist"""
    sp = get_spotify_client()
    
    try:
        playlist = sp.playlist(playlist_id)
        share_url = playlist['external_urls']['spotify']
        
        return render_template('share_playlist.html', 
                            share_url=share_url, 
                            playlist_name=playlist['name'])
    
    except Exception as e:
        flash(f"Errore nel recuperare il link di condivisione: {str(e)}", "danger")
        return redirect(url_for('home.view_saved_playlists'))



@home_bp.route('/home')
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
        playlists = sp_public.search(q='top playlists', type='playlist', limit=10)['playlists']['items']
    
    search_results = []
    if request.method == 'POST':
        query = request.form.get('search_query')
        if query:
            search_results = search_spotify(query)
    
    return render_template('home.html', user_info=user_info, playlists=playlists, search_results=search_results)

@home_bp.route('/compare_playlists', methods=['POST'])
def compare_playlists():
    selected_ids = request.form.getlist('playlist_ids')
    if len(selected_ids) < 2:
        flash("Seleziona almeno due playlist.")
        return redirect(url_for('home.saved_playlists'))

    sp = get_spotify_client()
    artist_genres = {}

    playlists_data = []
    track_sets = []
    artist_sets = []
    popularity_lists = []
    genre_counts = []
    release_years = []

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = []
        for playlist_id in selected_ids:
            futures.append(executor.submit(fetch_playlist_data, sp, playlist_id, artist_genres))
        
        for future in futures:
            data = future.result()
            if data:
                playlists_data.append(data['playlist'])
                track_sets.append(data['track_set'])
                artist_sets.append(data['artist_set'])
                popularity_lists.append(data['popularity'])
                genre_counts.append(data['genre_count'])
                release_years.append(data['year_count'])

    if not playlists_data:
        flash("Nessun dato disponibile per il confronto.", "warning")
        return redirect(url_for('home.view_saved_playlists'))

    common_tracks = set.intersection(*track_sets)
    smallest_len = min(len(p['tracks']) for p in playlists_data)
    similarity_percent = round((len(common_tracks) / smallest_len) * 100, 2)

    playlist_data = {
        'playlists': playlists_data,
        'commonTracks': list(common_tracks),
        'similarityPercent': similarity_percent,
        'trackData': [len(p['tracks']) for p in playlists_data],
        'artistData': [list(set(p['artists'])) for p in playlists_data],
        'popularityData': [sum(p['popularity']) / len(p['popularity']) if p['popularity'] else 0 for p in playlists_data],
        'genreData': [dict(counter) for counter in genre_counts],
        'yearData': [dict(counter) for counter in release_years],
    }

    return render_template('compare_playlists.html', playlist_data=playlist_data)

@home_bp.route('/playlist_analysis/<playlist_id>')
def playlist_analysis(playlist_id):
    sp = get_spotify_client()
    tracks_data = []

    try:
        # Retrieve all tracks using pagination
        tracks = []
        results = sp.playlist_tracks(playlist_id)
        while results:
            tracks.extend(results.get('items', []))
            if results.get('next'):
                results = sp.next(results)
            else:
                break

        # Process tracks efficiently
        for track in tracks:
            if not track or 'track' not in track or track['track'] is None:
                continue

            track_info = track['track']
            artist_info = track_info.get('artists', [{}])[0]
            artist_id = artist_info.get('id')
            genre = 'Unknown'

            if artist_id:
                try:
                    # Cache artist data to avoid repeated API calls
                    if artist_id not in artist_genres:
                        artist_data = sp.artist(artist_id)
                        artist_genres[artist_id] = artist_data.get('genres', [])
                    genre = artist_genres[artist_id][0] if artist_genres[artist_id] else 'Unknown'
                except Exception as e:
                    print(f"Error fetching genre for artist {artist_id}: {e}")

            track_data = {
                'track_name': track_info.get('name', 'Unknown'),
                'artist_name': artist_info.get('name', 'Unknown'),
                'album_name': track_info.get('album', {}).get('name', 'Unknown'),
                'genre': genre,
                'release_year': track_info.get('album', {}).get('release_date', '').split('-')[0] if track_info.get('album', {}).get('release_date') else None,
                'duration_min': round(track_info.get('duration_ms', 0) / 60000, 2),
                'popularity': track_info.get('popularity', 0)
            }
            tracks_data.append(track_data)

        if not tracks_data:
            flash("No tracks found in the playlist.", "warning")
            return redirect(url_for('home.view_saved_playlists'))

        # Create DataFrame with minimal data
        df = pd.DataFrame(tracks_data)

        # Calculate top artists, albums, genres, etc., efficiently
        top_artists = df['artist_name'].value_counts().head(5)
        top_albums = df['album_name'].value_counts().head(5)
        genre_distribution = df['genre'].value_counts()
        release_counts = df['release_year'].value_counts().sort_index()

        # Calculate the average popularity per release year
        df['release_year'] = pd.to_numeric(df['release_year'])
        yearly_popularity = df.groupby('release_year')['popularity'].mean().reset_index()
        yearly_popularity = yearly_popularity.sort_values(by='release_year')

        # Create visualizations
        year_fig = px.bar(x=release_counts.index, y=release_counts.values,
                         labels={'x': 'Release Year', 'y': 'Number of Tracks'},
                         title='Tracks per Release Year')

        artist_fig = px.bar(top_artists, x=top_artists.index, y=top_artists.values,
                           labels={'x': 'Artist', 'y': 'Number of Tracks'})

        album_fig = px.bar(top_albums, x=top_albums.index, y=top_albums.values,
                          labels={'x': 'Album', 'y': 'Number of Tracks'})

        genre_fig = px.pie(genre_distribution, names=genre_distribution.index,
                          values=genre_distribution.values, title='Genre Distribution')

        popularity_fig = px.histogram(df, x='popularity',
                                     nbins=20,
                                     title="Popularity Distribution",
                                     labels={'popularity': 'Popularity Score'})

        duration_fig = px.histogram(df, x='duration_min',
                                   title='Track Duration Distribution')

        # Create the popularity evolution line chart
        popularity_fig_time = px.line(yearly_popularity, 
                                     x='release_year', 
                                     y='popularity',
                                     labels={'release_year': 'Release Year', 
                                             'popularity': 'Average Popularity'},
                                     title='Evolution of Popularity Over Time')

        return render_template('playlist_analysis.html',
                             artist_fig=artist_fig.to_html(full_html=False),
                             album_fig=album_fig.to_html(full_html=False),
                             genre_fig=genre_fig.to_html(full_html=False),
                             year_fig=year_fig.to_html(full_html=False),
                             duration_fig=duration_fig.to_html(full_html=False),
                             popularity_fig=popularity_fig.to_html(full_html=False),
                             popularity_fig_time=popularity_fig_time.to_html(full_html=False))

    except Exception as e:
        flash(f"Error during playlist analysis: {e}", "danger")
        return redirect(url_for('home.view_saved_playlists'))


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
    """Effettua la ricerca di playlist su Spotify e mostra raccomandazioni correlate"""
    sp = get_spotify_client()
    search_results = []
    recommendations = []
    
    if request.method == 'POST':
        query = request.form.get('search_query')
        if query:
            try:
                # Ricerca playlist
                search_results = sp.search(q=query, type='playlist', limit=10)['playlists']['items']
                
                # Filtra le playlist con zero canzoni e None
                search_results = [
                    p for p in search_results 
                    if p is not None and 'tracks' in p and p['tracks'] is not None and 'total' in p['tracks'] and p['tracks']['total'] > 0
                ]
                
                # Se non sei autenticato, usa le raccomandazioni basate sulla query
                if 'token_info' not in session:
                    try:
                        # Cerca una playlist pubblica con un nome simile alla query
                        public_playlists = sp.search(q=f"{query} playlist", type='playlist', limit=1)['playlists']['items']
                        if public_playlists:
                            public_playlist_id = public_playlists[0]['id']
                            # Ottieni le prime 5 tracce della playlist pubblica
                            public_tracks = sp.playlist_tracks(public_playlist_id, limit=5)['items']
                            recommendations = [{
                                'name': track['track']['name'],
                                'artists': track['track']['artists'],
                                'external_urls': {'spotify': track['track']['external_urls']['spotify']}
                            } for track in public_tracks]
                        else:
                            # Se non trovi playlist, cerca canzoni dell'artista
                            tracks = sp.search(q=f"artist:{query}", type='track', limit=5)['tracks']['items']
                            recommendations = [{
                                'name': track['name'],
                                'artists': track['artists'],
                                'external_urls': {'spotify': track['external_urls']['spotify']}
                            } for track in tracks]
                    except Exception as e:
                        print(f"Errore nel recupero delle raccomandazioni pubbliche: {e}")
                else:
                    # Se autenticato, usa le raccomandazioni di Spotify
                    recommendations_response = sp.recommendations(
                        query=query,
                        limit=5
                    )
                    recommendations = recommendations_response.get('tracks', [])
                
            except Exception as e:
                print(f"Errore nella ricerca: {e}")
                flash(f"Errore nella ricerca: {str(e)}", "danger")
    
    return render_template('home.html', 
                         search_results=search_results,
                         recommendations=recommendations,
                         user_info=session.get('user_info'), 
                         playlists=session.get('playlists', []))
    
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



@home_bp.route('/remove_saved_playlist/<playlist_id>', methods=['POST'])
def remove_saved_playlist(playlist_id):
    """Rimuove una playlist salvata dal database o dalla sessione."""
    if current_user.is_authenticated:
        try:
            conn = get_db()
            with conn.cursor() as cursor:
                cursor.execute('DELETE FROM saved_playlists WHERE user_id = %s AND playlist_id = %s', 
                               (current_user.id, playlist_id))
                conn.commit()
            conn.close()
            flash("Playlist rimossa dal tuo profilo!", "success")
        except Exception as e:
            flash(f"Errore nel rimuovere la playlist: {e}", "danger")
    else:
        if playlist_id in session.get('saved_playlists', []):
            session['saved_playlists'].remove(playlist_id)
            session.modified = True
            flash("Playlist rimossa temporaneamente dalla sessione.", "info")
    
    return redirect(url_for('home.view_saved_playlists'))
    
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
