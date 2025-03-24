# Importazione delle librerie necessarie
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required
from services.db import get_db  # Funzione per interagire con il database
from werkzeug.security import check_password_hash, generate_password_hash  # Per l'hashing delle password
from models.user import User  # Modello User per creare oggetti utente

# Creazione di un Blueprint per le rotte relative al login
login_bp = Blueprint('login_bp', __name__)


# Rotta per il login dell'utente
@login_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db()
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            user_data = cursor.fetchone()
        conn.close()

        if user_data:
            if check_password_hash(user_data['password_hash'], password):
                user = User(user_data['id'], user_data['username'], user_data['email'])
                login_user(user)
                flash('Login effettuato con successo!', 'success')
                return redirect(url_for('home.homepage'))
            else:
                flash('Password errata. Riprova.', 'danger')
        else:
            flash('Utente non trovato.', 'danger')

    return render_template('login.html')

# Rotta per la registrazione utente
@login_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        password_hash = generate_password_hash(password)

        conn = get_db()
        with conn.cursor() as cursor:
            try:
                # Verifica se username esiste
                cursor.execute("SELECT 1 FROM users WHERE username = %s", (username,))
                if cursor.fetchone():
                    flash('Username già in uso. Scegli un altro nome utente.', 'danger')
                    return render_template("registrazione.html")

                # Verifica se email esiste
                cursor.execute("SELECT 1 FROM users WHERE email = %s", (email,))
                if cursor.fetchone():
                    flash('Email già registrata. Usa un\'altra email.', 'danger')
                    return render_template("registrazione.html")

                # Inserisci nuovo utente
                cursor.execute(
                    "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
                    (username, email, password_hash)
                )
                conn.commit()
                flash("Registrazione completata! Ora puoi effettuare il login.", 'success')
                return redirect(url_for("login_bp.login"))

            except Exception as e:
                conn.rollback()
                flash("Errore durante la registrazione: " + str(e), 'danger')
                return render_template("registrazione.html")
        conn.close()

    return render_template("registrazione.html")


# Rotta per il logout

@login_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logout effettuato con successo.', 'success')
    return redirect(url_for('home.homepage'))
