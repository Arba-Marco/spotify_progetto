# Importazione delle librerie necessarie
import re
from flask import Blueprint, render_template, redirect, url_for, request, flash , session
from flask_login import login_user, logout_user, login_required
from services.db import get_db  # Funzione per interagire con il database
from werkzeug.security import check_password_hash, generate_password_hash  # Per l'hashing delle password
from models.user import User  # Modello User per creare oggetti utente
import os
from services.db import DatabaseWrapper  # Importa la classe DatabaseWrapper
from models.user import User  # Importa la classe User

login_bp = Blueprint('login_bp', __name__)
def validate_email(email):
    """Validazione del formato email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """Validazione complessità password"""
    if len(password) < 8:
        return False, "La password deve contenere almeno 8 caratteri"
    if not re.search(r'[A-Z]', password):
        return False, "La password deve contenere almeno una lettera maiuscola"
    if not re.search(r'[a-z]', password):
        return False, "La password deve contenere almeno una lettera minuscola"
    if not re.search(r'[0-9]', password):
        return False, "La password deve contenere almeno un numero"
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "La password deve contenere almeno un carattere speciale"
    return True, ""
# Rotta per il login
@login_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Crea una connessione al database tramite DatabaseWrapper
        db_wrapper = DatabaseWrapper(
            host=os.environ.get("MYSQL_HOST", "localhost"),
            user=os.environ.get("MYSQL_USER", "root"),
            password=os.environ.get("MYSQL_PASSWORD", "password"),
            database=os.environ.get("MYSQL_DATABASE", "spotify")
        )

        # Recupera i dati dell'utente dal database
        user_data = db_wrapper.fetch_query("SELECT * FROM users WHERE username = %s", (username,))
        
        if user_data:
            user_data = user_data[0]  # Prendi il primo (e unico) risultato
            if check_password_hash(user_data['password_hash'], password):
                # Crea un oggetto User
                user = User(user_data['id'], user_data['username'], user_data['email'])
                login_user(user)  # Effettua il login dell'utente
                flash("Accesso effettuato con successo.", "success")
                return redirect(url_for('home.homepage'))
            else:
                flash("Password errata. Controlla le tue credenziali e riprova.", "danger")
        else:
            flash("Utente non trovato. Verifica il tuo username.", "danger")
    return render_template('login.html')

# Rotta per la registrazione (aggiungi qui la logica della registrazione, se necessario)
@login_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')

        # Validazione input
        if not all([username, email, password, password_confirm]):
            flash("Tutti i campi sono obbligatori", "danger")
            return render_template("registrazione.html")

        if not validate_email(email):
            flash("Formato email non valido", "danger")
            return render_template("registrazione.html")

        is_valid_pw, pw_message = validate_password(password)
        if not is_valid_pw:
            flash(pw_message, "danger")
            return render_template("registrazione.html")

        if password != password_confirm:
            flash("Le password non coincidono", "danger")
            return render_template("registrazione.html")

        # Hash della password
        password_hash = generate_password_hash(password)

        # Connessione al database con gestione transazionale
        db_wrapper = DatabaseWrapper(
            host=os.environ.get("MYSQL_HOST", "localhost"),
            user=os.environ.get("MYSQL_USER", "root"),
            password=os.environ.get("MYSQL_PASSWORD", "password"),
            database=os.environ.get("MYSQL_DATABASE", "spotify")
        )

        try:
            # Inizia transazione
            conn = db_wrapper.connect()
            with conn.cursor() as cursor:
                # Verifica username esistente
                cursor.execute("SELECT 1 FROM users WHERE username = %s", (username,))
                if cursor.fetchone():
                    flash("Username già in uso", "danger")
                    return render_template("registrazione.html")

                # Verifica email esistente
                cursor.execute("SELECT 1 FROM users WHERE email = %s", (email,))
                if cursor.fetchone():
                    flash("Email già registrata", "danger")
                    return render_template("registrazione.html")

                # Inserimento utente
                cursor.execute(
                    "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
                    (username, email, password_hash)
                )
                conn.commit()
                flash("Registrazione completata con successo!", "success")
                return redirect(url_for("login_bp.login"))

        except pymysql.Error as e:
            conn.rollback()
            error_code = e.args[0]
            if error_code == 1062:  # Duplicate entry
                flash("Errore: username o email già esistenti", "danger")
            else:
                flash(f"Errore database: {str(e)}", "danger")
            return render_template("registrazione.html")
        finally:
            conn.close()

    return render_template("registrazione.html")
    
# Rotta per il logout
@login_bp.route('/logout')
@login_required
def logout():
    logout_user()
    session.pop('_flashes', None)  # Rimuove i messaggi flash
    return redirect(url_for('home.homepage'))
