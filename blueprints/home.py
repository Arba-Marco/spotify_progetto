from flask import Blueprint, render_template, session, redirect, url_for, request
import spotipy

home_bp = Blueprint('home', __name__)

@home_bp.route('/home', methods=['GET', 'POST'])
def homepage():
    token_info = session.get('token_info', None)
    if not token_info:
        return redirect(url_for('auth.login'))

    sp = spotipy.Spotify(auth=token_info['access_token'])
    user_info = sp.current_user()
    playlists = sp.current_user_playlists()['items']

    search_results = []
    if request.method == 'POST':
        query = request.form.get('search_query')
        if query:
            search_results = search_spotify(sp, query)

    return render_template('home.html', user_info=user_info, playlists=playlists, search_results=search_results)

@home_bp.route('/playlist_tracks.html/<playlist_id>')
def playlist_tracks(playlist_id):
    token_info = session.get('token_info', None)
    if not token_info:
        return redirect(url_for('auth.login'))

    sp = spotipy.Spotify(auth=token_info['access_token'])
    tracks = sp.playlist_tracks(playlist_id)['items']

    return render_template('playlist_tracks.html', tracks=tracks)

def search_spotify(sp, query):
    """Funzione per cercare brani, album o artisti su Spotify."""
    result = sp.search(q=query, type='track', limit=10)
    return result['tracks']['items']
