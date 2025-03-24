import os
import pymysql

class DatabaseWrapper:
    def __init__(self, host, user, password, database):
        # Configurazione della connessione usando le variabili d'ambiente
        self.db_config = {
            'host': host,
            'user': user,
            'password': password,
            'database': database,
            'cursorclass': pymysql.cursors.DictCursor
        }
        # Creazione delle tabelle all'avvio
        self.create_tables()

    def connect(self):
        return pymysql.connect(**self.db_config)

    def execute_query(self, query, params=()):
        conn = self.connect()
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            conn.commit()
        conn.close()

    def fetch_query(self, query, params=()):
        conn = self.connect()
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            result = cursor.fetchall()
        conn.close()
        return result

    def create_tables(self):
        # Tabella utenti
        self.execute_query('''
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(100) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL
            )
        ''')

        # Tabella playlist salvate
        self.execute_query('''
            CREATE TABLE IF NOT EXISTS saved_playlists (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                playlist_id VARCHAR(100) NOT NULL,
                playlist_name VARCHAR(255),
                UNIQUE(user_id, playlist_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')

# Funzione helper per ottenere una connessione al database utilizzando variabili d'ambiente
def get_db():
    return pymysql.connect(
        host=os.environ.get("MYSQL_HOST", "localhost"),
        user=os.environ.get("MYSQL_USER", "root"),
        password=os.environ.get("MYSQL_PASSWORD", "password"),
        database=os.environ.get("MYSQL_DATABASE", "spotify"),
        cursorclass=pymysql.cursors.DictCursor
    )

# Per testare in modalità standalone 
if __name__ == "__main__":
    db_wrapper = DatabaseWrapper(
        host=os.environ.get("MYSQL_HOST", "localhost"),
        user=os.environ.get("MYSQL_USER", "root"),
        password=os.environ.get("MYSQL_PASSWORD", "password"),
        database=os.environ.get("MYSQL_DATABASE", "spotify")
    )
    print("Tabelle 'users' e 'saved_playlists' create (se non esistenti).")
