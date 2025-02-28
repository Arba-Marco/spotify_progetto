import spotipy  # Importa la libreria Spotipy per interagire con l'API di Spotify
from spotipy.oauth2 import SpotifyOAuth  # Importa la classe per l'autenticazione OAuth di Spotify
from flask import session  # Importa la sessione di Flask per memorizzare i token dell'utente

class SpotifyAuthService:
    def __init__(self, client_id, client_secret, redirect_uri):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        # Configura il flusso OAuth per ottenere l'autenticazione dell'utente
        self.sp_oauth = SpotifyOAuth(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
            scope="user-read-private",  # Definisce il livello di accesso richiesto
            show_dialog=True  # Mostra sempre la finestra di dialogo di autenticazione
        )

    def get_authorize_url(self):
        """Genera e restituisce l'URL di autorizzazione di Spotify"""
        return self.sp_oauth.get_authorize_url()

    def get_access_token(self, code):
        """Scambia il codice di autorizzazione per un token di accesso"""
        return self.sp_oauth.get_access_token(code)

    def save_token_to_session(self, token_info):
        """Salva le informazioni del token nella sessione"""
        session['token_info'] = token_info

    def clear_token_from_session(self):
        """Rimuove il token dalla sessione"""
        session.clear()

    def get_public_spotify_client(self):
        """Restituisce un client pubblico di Spotify senza necessità di login."""
        return spotipy.Spotify()  # Client senza autenticazione, per fare ricerche pubbliche
