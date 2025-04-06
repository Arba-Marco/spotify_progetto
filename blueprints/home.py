from flask import Blueprint, render_template, request, session, flash, redirect, url_for
import spotipy
from spotipy.oauth2 import SpotifyOAuth, SpotifyClientCredentials
from flask_login import current_user
from services.db import get_db
import pandas as pd
import plotly.express as px
import pymysql
import os
from pymysql.cursors import DictCursor
from collections import defaultdict

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
    """Restituisce un client Spotify autenticato oppure un client pubblico se l'utente non è loggato."""
    token_info = session.get('token_info')
    if token_info:
        return spotipy.Spotify(auth=token_info['access_token'])
    return sp_public


def get_playlist_data(sp, playlist_id):
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

def compare_playlist_data(playlist1, playlist2):
    """Esegue il confronto tra due playlist."""
    results = {}
    
    # 1. Brani in comune
    tracks1 = {track['track_id']: track for track in playlist1['tracks'] if track['track_id']}
    tracks2 = {track['track_id']: track for track in playlist2['tracks'] if track['track_id']}
    
    common_tracks = set(tracks1.keys()).intersection(set(tracks2.keys()))
    results['common_tracks'] = {
        'count': len(common_tracks),
        'tracks': [tracks1[track_id] for track_id in common_tracks],
        'percentage_playlist1': (len(common_tracks) / playlist1['total_tracks']) * 100 if playlist1['total_tracks'] > 0 else 0,
        'percentage_playlist2': (len(common_tracks) / playlist2['total_tracks']) * 100 if playlist2['total_tracks'] > 0 else 0
    }
    
    # 2. Artisti in comune
    artists1 = defaultdict(int)
    artists2 = defaultdict(int)
    
    for track in playlist1['tracks']:
        artists1[track['artist_name']] += 1
    
    for track in playlist2['tracks']:
        artists2[track['artist_name']] += 1
    
    common_artists = set(artists1.keys()).intersection(set(artists2.keys()))
    results['common_artists'] = {
        'count': len(common_artists),
        'artists': [
            {
                'name': artist,
                'count_playlist1': artists1[artist],
                'count_playlist2': artists2[artist]
            } 
            for artist in common_artists
        ]
    }
    
    # 3. Popolarità media
    popularity1 = [track['popularity'] for track in playlist1['tracks'] if 'popularity' in track]
    popularity2 = [track['popularity'] for track in playlist2['tracks'] if 'popularity' in track]
    
    results['popularity_comparison'] = {
        'playlist1_avg': sum(popularity1) / len(popularity1) if popularity1 else 0,
        'playlist2_avg': sum(popularity2) / len(popularity2) if popularity2 else 0
    }
    
    # 4. Confronto generi musicali
    genres1 = defaultdict(int)
    genres2 = defaultdict(int)
    
    for track in playlist1['tracks']:
        genres1[track['genre']] += 1
    
    for track in playlist2['tracks']:
        genres2[track['genre']] += 1
    
    all_genres = set(genres1.keys()).union(set(genres2.keys()))
    results['genre_comparison'] = {
        'genres': [
            {
                'name': genre,
                'count_playlist1': genres1.get(genre, 0),
                'count_playlist2': genres2.get(genre, 0)
            }
            for genre in all_genres
        ]
    }
    
    # 5. Durata media
    duration1 = [track['duration_ms'] for track in playlist1['tracks'] if 'duration_ms' in track]
    duration2 = [track['duration_ms'] for track in playlist2['tracks'] if 'duration_ms' in track]
    
    results['duration_comparison'] = {
        'playlist1_avg': sum(duration1) / len(duration1) / 60000 if duration1 else 0,  # Converti in minuti
        'playlist2_avg': sum(duration2) / len(duration2) / 60000 if duration2 else 0
    }
    
    return results


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

@home_bp.route('/compare_playlists', methods=['GET', 'POST'])
def compare_playlists():
    """Gestisce la comparazione tra due playlist salvate (per utenti loggati e non loggati)."""
    sp = get_spotify_client()
    playlist1_data = None
    playlist2_data = None
    comparison_results = None

    if current_user.is_authenticated:
        # Se l'utente è autenticato, recupera le playlist salvate dal database
        try:
            conn = get_db()
            with conn.cursor() as cursor:
                cursor.execute('SELECT playlist_id FROM saved_playlists WHERE user_id = %s', (current_user.id,))
                saved_playlists = cursor.fetchall()
                playlist_ids = [playlist[0] for playlist in saved_playlists]  # Lista degli ID delle playlist salvate
            conn.close()

            playlists = []
            for playlist_id in playlist_ids:
                playlist_data = get_playlist_data(sp, playlist_id)
                if playlist_data:
                    playlists.append(playlist_data)

        except Exception as e:
            flash(f"Errore nel recupero delle playlist salvate: {e}", "danger")
            return redirect(url_for('home.homepage'))

    else:
        # Se l'utente non è autenticato, recupera le playlist salvate dalla sessione
        playlists = []
        if 'saved_playlists' in session:
            for playlist_id in session['saved_playlists']:
                playlist_data = get_playlist_data(sp, playlist_id)
                if playlist_data:
                    playlists.append(playlist_data)

    # Se l'utente ha selezionato due playlist da confrontare
    if request.method == 'POST':
        playlist1_id = request.form.get('playlist1_id')
        playlist2_id = request.form.get('playlist2_id')

        # Trova le due playlist selezionate
        playlist1_data = next((p for p in playlists if p['id'] == playlist1_id), None)
        playlist2_data = next((p for p in playlists if p['id'] == playlist2_id), None)

        if playlist1_data and playlist2_data:
            comparison_results = compare_playlist_data(playlist1_data, playlist2_data)

    # Crea grafici con Plotly
    graphs = {}
    if comparison_results:
        # Grafico brani in comune
        graphs['common_tracks'] = px.bar(
            x=[playlist1_data['name'], playlist2_data['name'], 'Brani in comune'],
            y=[playlist1_data['total_tracks'], playlist2_data['total_tracks'], comparison_results['common_tracks']['count']],
            labels={'x': 'Playlist', 'y': 'Numero di brani'},
            title='Confronto numero brani e brani in comune',
            color=['Playlist 1', 'Playlist 2', 'Comune'],
            color_discrete_map={'Playlist 1': '#1DB954', 'Playlist 2': '#191414', 'Comune': '#535353'}
        )
        
        # Grafico popolarità media
        graphs['popularity'] = px.bar(
            x=[playlist1_data['name'], playlist2_data['name']],
            y=[comparison_results['popularity_comparison']['playlist1_avg'], 
               comparison_results['popularity_comparison']['playlist2_avg']],
            labels={'x': 'Playlist', 'y': 'Popolarità media'},
            title='Confronto popolarità media',
            color=[playlist1_data['name'], playlist2_data['name']],
            color_discrete_map={playlist1_data['name']: '#1DB954', playlist2_data['name']: '#191414'}
        )
        
        # Grafico durata media
        graphs['duration'] = px.bar(
            x=[playlist1_data['name'], playlist2_data['name']],
            y=[comparison_results['duration_comparison']['playlist1_avg'], 
               comparison_results['duration_comparison']['playlist2_avg']],
            labels={'x': 'Playlist', 'y': 'Durata media (minuti)'},
            title='Confronto durata media brani',
            color=[playlist1_data['name'], playlist2_data['name']],
            color_discrete_map={playlist1_data['name']: '#1DB954', playlist2_data['name']: '#191414'}
        )
        
        # Grafico artisti in comune (top 10)
        if comparison_results['common_artists']['artists']:
            common_artists = sorted(
                comparison_results['common_artists']['artists'],
                key=lambda x: x['count_playlist1'] + x['count_playlist2'],
                reverse=True
            )[:10]
            
            artists_names = [a['name'] for a in common_artists]
            count1 = [a['count_playlist1'] for a in common_artists]
            count2 = [a['count_playlist2'] for a in common_artists]
            
            graphs['common_artists'] = px.bar(
                x=artists_names,
                y=[count1, count2],
                barmode='group',
                labels={'x': 'Artista', 'y': 'Numero di brani'},
                title='Top 10 artisti in comune',
                color=[playlist1_data['name'], playlist2_data['name']],
                color_discrete_map={playlist1_data['name']: '#1DB954', playlist2_data['name']: '#191414'}
            )
    
    return render_template('templates/compare_playlists.html',
                         playlist1_data=playlist1_data,
                         playlist2_data=playlist2_data,
                         comparison_results=comparison_results,
                         graphs={k: v.to_html(full_html=False) for k, v in graphs.items()})


@home_bp.route('/playlist_analysis/<playlist_id>')
def playlist_analysis(playlist_id):
    sp = get_spotify_client()
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

            release_date = track_info.get('album', {}).get('release_date')
            year = None
            if release_date:
                year = release_date.split('-')[0]

            duration_ms = track_info.get('duration_ms', 0)
            duration_min = round(duration_ms / 60000, 2)

            popularity = track_info.get('popularity', 0)

            track_data = {
                'track_name': track_info.get('name', 'Sconosciuto'),
                'artist_name': artist_info.get('name', 'Sconosciuto'),
                'album_name': track_info.get('album', {}).get('name', 'Sconosciuto'),
                'genre': genre,
                'release_year': year,
                'duration_min': duration_min,
                'popularity': popularity
            }
            tracks_data.append(track_data)
    except Exception as e:
        flash(f"Errore durante l'analisi della playlist: {e}", "danger")
        return redirect(url_for('home.view_saved_playlists'))

    if not tracks_data:
        flash("Nessuna traccia trovata nella playlist.", "warning")
        return redirect(url_for('home.view_saved_playlists'))

    df = pd.DataFrame(tracks_data)

    top_artists = df['artist_name'].value_counts().head(5)
    top_albums = df['album_name'].value_counts().head(5)
    genre_distribution = df['genre'].value_counts()
    release_counts = df['release_year'].value_counts().sort_index()

    year_fig = px.bar(x=release_counts.index, y=release_counts.values,
                      labels={'x': 'Anno di Pubblicazione', 'y': 'Numero di Brani'},
                      title='Brani Pubblicati per Anno')

    artist_fig = px.bar(top_artists, x=top_artists.index, y=top_artists.values,
                        labels={'x': 'Artista', 'y': 'Numero di brani'})
    album_fig = px.bar(top_albums, x=top_albums.index, y=top_albums.values,
                       labels={'x': 'Album', 'y': 'Numero di brani'})
    genre_fig = px.pie(genre_distribution, names=genre_distribution.index,
                       values=genre_distribution.values, title='Distribuzione dei generi musicali')

    # Grafico della popolarità (normale)
    popularity_fig = px.histogram(df, 
                               x='popularity', 
                               nbins=20,  # Aumenta il numero di bin per una visualizzazione più dettagliata
                               title="Distribuzione della Popolarità dei Brani",
                               labels={'popularity': 'Popolarità'},
                               color_discrete_sequence=['mediumseagreen'])

    popularity_fig.update_xaxes(range=[0, 100], tick0=0, dtick=5)  # Intervallo da 0 a 100 con un passo di 5
    popularity_fig.update_layout(bargap=0.2)  # Riduce lo spazio tra le barre per una visualizzazione migliore

    # Grafico della popolarità nel tempo (media per anno)
    popularity_fig_time = px.bar(df.groupby('release_year')['popularity'].mean().reset_index(), 
                                  x='release_year', y='popularity', 
                                  labels={'release_year': 'Anno di Pubblicazione', 'popularity': 'Popolarità Media'},
                                  title='Evoluzione della Popolarità nel Tempo')

    # Grafico della durata dei brani
    bins = [round(x * 0.25, 2) for x in range(0, 41)]  # 0 to 10 minutes in 15 sec steps
    duration_fig = px.histogram(df, x='duration_min',
                                category_orders={"duration_min": bins},
                                labels={'duration_min': 'Durata (minuti)'},
                                title='Distribuzione della Durata dei Brani nella Playlist',
                                color_discrete_sequence=['#00BFFF'])
    duration_fig.update_xaxes(dtick=0.5)  # visualizza un tick ogni 30 sec
    duration_fig.update_layout(bargap=0.2)

    return render_template('playlist_analysis.html',
                           artist_fig=artist_fig.to_html(full_html=False),
                           album_fig=album_fig.to_html(full_html=False),
                           genre_fig=genre_fig.to_html(full_html=False),
                           year_fig=year_fig.to_html(full_html=False),
                           duration_fig=duration_fig.to_html(full_html=False),
                           popularity_fig=popularity_fig.to_html(full_html=False),
                           popularity_fig_time=popularity_fig_time.to_html(full_html=False))



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
