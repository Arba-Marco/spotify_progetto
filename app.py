from flask import Flask  # Importa Flask per creare l'applicazione web
from flask_login import LoginManager
from blueprints.auth import auth_bp  # Importa il Blueprint per la gestione dell'autenticazione
from blueprints.home import home_bp  # Importa il Blueprint per la gestione della homepage
from blueprints.login import login_bp  # Importa il Blueprint per il login
from services.db import get_db
from models.user import User

app = Flask(__name__)  # Crea un'istanza dell'app Flask
app.secret_key = 'chiave_per_session'  # Imposta una chiave segreta per gestire le sessioni utente
app.config['SESSION_PERMANENT'] = True
app.config['SESSION_TYPE'] = 'filesystem'  # Usa il filesystem per le sessioni

login_manager = LoginManager()
login_manager.login_view = "login.login"  # Indica la route di login
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    """ Carica un utente dal database dato il suo ID """
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user_data = cursor.fetchone()

    if user_data:
        return User(user_data[0], user_data[1], user_data[2])  # id, username, email
    return None

# Registriamo i Blueprint per modularizzare il codice
app.register_blueprint(auth_bp)
app.register_blueprint(home_bp)
app.register_blueprint(login_bp, url_prefix="/auth")  # Blueprint per il login

if __name__ == '__main__':
    app.run(debug=True)