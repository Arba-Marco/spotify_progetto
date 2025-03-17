import pymysql

# Connessione al server MySQL
conn = pymysql.connect(
    host='localhost',  # o l'indirizzo IP del tuo server
    user='root',       # il tuo nome utente MySQL
    password='password',  # la tua password MySQL
)

# Creazione di un cursore per eseguire le query
cursor = conn.cursor()

# Creazione del database
cursor.execute("CREATE DATABASE IF NOT EXISTS spotify_db")

# Selezione del database appena creato
cursor.execute("USE spotify_db")

# Creazione della tabella utenti
cursor.execute("""
CREATE TABLE IF NOT EXISTS utenti (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100),
    email VARCHAR(100) UNIQUE,
    data_registrazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# Creazione della tabella playlist
cursor.execute("""
CREATE TABLE IF NOT EXISTS playlist (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100),
    descrizione TEXT,
    id_utente INT,
    data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_utente) REFERENCES utenti(id) ON DELETE CASCADE
)
""")

# Inserimento di dati di esempio nella tabella utenti
cursor.execute("INSERT INTO utenti (nome, email) VALUES (%s, %s)", ('Mario Rossi', 'mario.rossi@example.com'))
cursor.execute("INSERT INTO utenti (nome, email) VALUES (%s, %s)", ('Luigi Bianchi', 'luigi.bianchi@example.com'))

# Recupero dell'ID dell'utente appena inserito per l'uso nelle playlist
cursor.execute("SELECT id FROM utenti WHERE email = %s", ('mario.rossi@example.com',))
id_utente_mario = cursor.fetchone()[0]

# Inserimento di playlist per l'utente Mario Rossi
cursor.execute("INSERT INTO playlist (nome, descrizione, id_utente) VALUES (%s, %s, %s)", 
               ('Rock Classics', 'Le migliori canzoni rock', id_utente_mario))
cursor.execute("INSERT INTO playlist (nome, descrizione, id_utente) VALUES (%s, %s, %s)", 
               ('Jazz Hits', 'Le canzoni jazz più popolari', id_utente_mario))

# Commit delle modifiche
conn.commit()

# Recupero delle playlist di Mario Rossi
cursor.execute("""
SELECT p.nome, p.descrizione
FROM playlist p
JOIN utenti u ON p.id_utente = u.id
WHERE u.email = %s
""", ('mario.rossi@example.com',))

playlists_mario = cursor.fetchall()
print(f"Playlist di Mario Rossi:")
for playlist in playlists_mario:
    print(f"- {playlist[0]}: {playlist[1]}")

# Chiusura della connessione
cursor.close()
conn.close()