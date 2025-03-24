import os
from flask import Flask
from flask_login import LoginManager
from blueprints.auth import auth_bp      # Blueprint per l'autenticazione (Spotify)
from blueprints.home import home_bp      # Blueprint per la homepage
from blueprints.login import login_bp    # Blueprint per il login con Flask-Login
from services.db import get_db, DatabaseWrapper
from models.user import User

app = Flask(__name__)
app.secret_key = 'chiave_per_session'
app.config['SESSION_PERMANENT'] = True
app.config['SESSION_TYPE'] = 'filesystem'

# Configurazione di Flask-Login
login_manager = LoginManager()
login_manager.login_view = "login_bp.login"  # Imposta la route di login del blueprint login_bp
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    """Carica un utente dal database dato il suo ID"""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user_data = cursor.fetchone()
    db.close()
    if user_data:
        # Assumiamo che user_data sia un dizionario con chiavi: 'id', 'username', 'email'
        return User(user_data['id'], user_data['username'], user_data['email'])
    return None

# Istanzia il DatabaseWrapper per creare le tabelle all'avvio (se non esistono)
db_wrapper = DatabaseWrapper(
    host=os.environ.get("MYSQL_HOST", "localhost"),
    user=os.environ.get("MYSQL_USER", "root"),
    password=os.environ.get("MYSQL_PASSWORD", "password"),
    database=os.environ.get("MYSQL_DATABASE", "spotify")
)

# Registrazione dei Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(home_bp)
app.register_blueprint(login_bp, url_prefix="/auth")

if __name__ == '__main__':
    app.run(debug=True)
