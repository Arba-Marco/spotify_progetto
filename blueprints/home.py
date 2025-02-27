from flask import Blueprint, render_template, session, redirect, url_for, request  # Importa le funzioni necessarie da Flask
import spotipy  # Libreria per interagire con l'API di Spotify

# Crea un Blueprint per la gestione delle pagine dell'applicazione
home_bp = Blueprint('home', __name__)

@home_bp.route('/home', methods=['GET', 'POST'])
def homepage():
    token_info = session.get('token_info', None)  # Recupera il token dalla sessione
    if not token_info:
        return redirect(url_for('auth.login'))  # Reindirizza al login se il token non è presente

    sp = spotipy.Spotify(auth=token_info['access_token'])  # Inizializza l'istanza di Spotipy con il token
    user_info = sp.current_user()  # Recupera le informazioni dell'utente autenticato
    playlists = sp.current_user_playlists()['items']  # Ottiene le playlist dell'utente

    search_results = []  # Inizializza la lista dei risultati della ricerca
    if request.method == 'POST':  # Se l'utente invia un modulo di ricerca
        query = request.form.get('search_query')  # Recupera la query di ricerca dall'input dell'utente
        if query:
            search_results = search_spotify(sp, query)  # Esegue la ricerca su Spotify

    # Renderizza la pagina home.html con i dati dell'utente, le playlist e i risultati della ricerca
    return render_template('home.html', user_info=user_info, playlists=playlists, search_results=search_results)


@home_bp.route('/playlist_tracks.html/<playlist_id>')
def playlist_tracks(playlist_id):
    token_info = session.get('token_info', None)  # Recupera il token dalla sessione
    if not token_info:
        return redirect(url_for('auth.login'))  # Reindirizza al login se il token non è presente

    sp = spotipy.Spotify(auth=token_info['access_token'])  # Inizializza l'istanza di Spotipy con il token
    tracks = sp.playlist_tracks(playlist_id)['items']  # Recupera le tracce della playlist specificata

    return render_template('playlist_tracks.html', tracks=tracks)  # Renderizza la pagina con le tracce della playlist

def search_spotify(sp, query):
    result = sp.search(q=query, type='playlist', limit=20)  # Esegue la ricerca di playlist su Spotify
    playlists = result['playlists']['items']  # Estrae le playlist dai risultati della ricerca
    
    # Aggiunge un controllo per evitare playlist con attributi non validi
    for playlist in playlists:
        if 'tracks' not in playlist:
            playlist['tracks'] = {'total': 0}  # Imposta un valore di default per il numero di tracce

    return playlists  # Restituisce la lista delle playlist trovate

