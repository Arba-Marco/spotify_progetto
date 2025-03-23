from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import login_user, logout_user, login_required
from services.db import get_db
from werkzeug.security import check_password_hash, generate_password_hash
from models.user import User  # Il costruttore di User deve accettare (id, username, email)

login_bp = Blueprint('login_bp', __name__)

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

        # Confronta la password inserita con il campo "password_hash" nel database
        if user_data and check_password_hash(user_data['password_hash'], password):
            user = User(user_data['id'], user_data['username'], user_data['email'])
            login_user(user)
            flash('Login effettuato con successo!', 'success')
            return redirect(url_for('home.homepage'))
        else:
            flash('Credenziali errate. Riprova.', 'danger')

    return render_template('login.html')

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
                cursor.execute(
                    "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
                    (username, email, password_hash)
                )
                conn.commit()
            except Exception as e:
                conn.close()
                flash("Errore durante la registrazione: " + str(e), 'danger')
                return render_template("registrazione.html")
        conn.close()

        flash("Registrazione completata! Ora puoi effettuare il login.", 'success')
        return redirect(url_for("login_bp.login"))
    return render_template("registrazione.html")

@login_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logout effettuato con successo.', 'success')
    return redirect(url_for('home.homepage'))
