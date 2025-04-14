# Importazione delle librerie necessarie
from flask import Blueprint, render_template, redirect, url_for, request, flash , session
from flask_login import login_user, logout_user, login_required
from services.db import get_db  # Funzione per interagire con il database
from werkzeug.security import check_password_hash, generate_password_hash  # Per l'hashing delle password
from models.user import User  # Modello User per creare oggetti utente
import os
from services.db import DatabaseWrapper  # Importa la classe DatabaseWrapper
from models.user import User  # Importa la classe User

login_bp = Blueprint('login_bp', __name__)

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
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        password_hash = generate_password_hash(password)

        # Crea una connessione al database tramite DatabaseWrapper
        db_wrapper = DatabaseWrapper(
            host=os.environ.get("MYSQL_HOST", "localhost"),
            user=os.environ.get("MYSQL_USER", "root"),
            password=os.environ.get("MYSQL_PASSWORD", "password"),
            database=os.environ.get("MYSQL_DATABASE", "spotify")
        )

        # Verifica se lo username è già in uso
        if db_wrapper.fetch_query("SELECT 1 FROM users WHERE username = %s", (username,)):
            flash("Il nome utente è già in uso. Scegli un altro nome utente.", "danger")
            return render_template("registrazione.html")

        # Verifica se l'email è già registrata
        if db_wrapper.fetch_query("SELECT 1 FROM users WHERE email = %s", (email,)):
            flash("Questa email è già registrata. Usa un'email diversa.", "danger")
            return render_template("registrazione.html")

        try:
            # Inserisci il nuovo utente nel database
            db_wrapper.execute_query(
                "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
                (username, email, password_hash)
            )
            flash("Registrazione completata con successo! Ora puoi effettuare il login.", "success")
            return redirect(url_for("login_bp.login"))
        except Exception as e:
            flash("Si è verificato un errore durante la registrazione: " + str(e), "danger")
            return render_template("registrazione.html")
        
    return render_template("registrazione.html")
    
# Rotta per il logout
@login_bp.route('/logout')
@login_required
def logout():
    logout_user()
    session.pop('_flashes', None)  # Rimuove i messaggi flash
    return redirect(url_for('home.homepage'))
