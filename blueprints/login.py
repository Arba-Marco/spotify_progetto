# Importazione delle librerie necessarie
from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import login_user, logout_user, login_required
from services.db import get_db  # Funzione per interagire con il database
from werkzeug.security import check_password_hash, generate_password_hash  # Per l'hashing delle password
from models.user import User  # Importazione del modello User per creare oggetti utente

# Creazione di un Blueprint per le rotte relative al login
login_bp = Blueprint('login_bp', __name__)

# Rotta per il login dell'utente
@login_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Gestione della sottomissione del modulo
    if request.method == 'POST':
        # Recupero dei dati dal modulo
        username = request.form['username']
        password = request.form['password']

        # Connessione al database e recupero dei dati dell'utente in base al nome utente
        conn = get_db()
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            user_data = cursor.fetchone()  # Recupera i dati dell'utente dal database
        conn.close()

        # Verifica della password inserita dall'utente
        if user_data and check_password_hash(user_data['password_hash'], password):
            # Se valida, crea un oggetto User e logga l'utente
            user = User(user_data['id'], user_data['username'], user_data['email'])
            login_user(user)
            flash('Login effettuato con successo!', 'success')  # Mostra un messaggio di successo
            return redirect(url_for('home.homepage'))  # Redirige alla homepage dopo un login riuscito
        else:
            flash('Credenziali errate. Riprova.', 'danger')  # Mostra un messaggio di errore se le credenziali sono sbagliate

    # Renderizza il template del login per le richieste GET
    return render_template('login.html')

# Rotta per la registrazione dell'utente
@login_bp.route('/register', methods=['GET', 'POST'])
def register():
    # Gestione della sottomissione del modulo
    if request.method == 'POST':
        # Recupero dei dati dal modulo
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        password_hash = generate_password_hash(password)  # Hash della password prima di salvarla nel DB

        # Connessione al database e inserimento dei dati del nuovo utente
        conn = get_db()
        with conn.cursor() as cursor:
            try:
                # Inserisce i dati del nuovo utente nel database
                cursor.execute(
                    "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
                    (username, email, password_hash)
                )
                conn.commit()  # Commette la transazione per salvare i dati
            except Exception as e:
                conn.close()
                flash("Errore durante la registrazione: " + str(e), 'danger')  # Mostra un messaggio di errore in caso di problemi
                return render_template("registrazione.html")  # Renderizza di nuovo la pagina di registrazione in caso di errore
        conn.close()

        flash("Registrazione completata! Ora puoi effettuare il login.", 'success')  # Mostra un messaggio di successo
        return redirect(url_for("login_bp.login"))  # Redirige alla pagina di login dopo una registrazione riuscita

    # Renderizza il template di registrazione per le richieste GET
    return render_template("registrazione.html")

# Rotta per il logout dell'utente
@login_bp.route('/logout')
@login_required  # Assicura che l'utente sia loggato prima di poter fare il logout
def logout():
    logout_user()  # Logga l'utente
    flash('Logout effettuato con successo.', 'success')  # Mostra un messaggio di successo
    return redirect(url_for('home.homepage'))  # Redirige alla homepage dopo il logout
