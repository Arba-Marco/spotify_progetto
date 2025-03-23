import pymysql

def get_db():
    return pymysql.connect(
        host="localhost",  # Assicurati che sia l'IP corretto (se Docker, potrebbe essere "127.0.0.1" o il nome del container)
        user="root",        # Cambia con il tuo utente MySQL
        password="password", # Cambia con la tua password MySQL
        database="spotify",  # Cambia con il nome del tuo database
        cursorclass=pymysql.cursors.DictCursor
    )