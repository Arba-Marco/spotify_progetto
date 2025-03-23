from flask import Blueprint, render_template, redirect, url_for, request, flash,session
from flask_login import login_user, logout_user, login_required, current_user
from services.db import get_db
from werkzeug.security import check_password_hash
from models.user import User

login_bp = Blueprint('login_bp', __name__)

@login_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user_data = cursor.fetchone()
        conn.close()

        if user_data and check_password_hash(user_data['password'], password):
            user = User(user_data['id'], user_data['username'])
            login_user(user)
            flash('Login effettuato con successo!', 'success')
            return redirect(url_for('home_bp.home'))
        else:
            flash('Credenziali errate. Riprova.', 'danger')

    return render_template('login.html')

@login_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logout effettuato con successo.', 'success')
    return redirect(url_for('home_bp.home'))
