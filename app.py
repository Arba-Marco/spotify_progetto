from flask import Flask  # Importa Flask per creare l'applicazione web
from blueprints.auth import auth_bp  # Importa il Blueprint per la gestione dell'autenticazione
from blueprints.home import home_bp  # Importa il Blueprint per la gestione della homepage

app = Flask(__name__)  # Crea un'istanza dell'app Flask
app.secret_key = 'chiave_per_session'  # Imposta una chiave segreta per gestire le sessioni utente
app.config['SESSION_PERMANENT'] = True
app.config['SESSION_TYPE'] = 'filesystem'  # Usa il filesystem per le sessioni
# Registriamo i Blueprint per modularizzare il codice
app.register_blueprint(auth_bp)  # Registra il Blueprint per l'autenticazione
app.register_blueprint(home_bp)  # Registra il Blueprint per la homepage

# Avvio dell'applicazione Flask in modalità debug (utile per lo sviluppo)
if __name__ == '__main__':
    app.run(debug=True)  # Esegue l'applicazione Flask in modalità debug
