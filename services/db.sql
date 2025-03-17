CREATE TABLE IF NOT EXISTS utenti (
    id INT AUTO_INCREMENT PRIMARY KEY,         
    nome VARCHAR(100) NOT NULL,                 
    email VARCHAR(100) NOT NULL UNIQUE,         
    data_registrazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP  
);
CREATE TABLE IF NOT EXISTS playlist (
    id INT AUTO_INCREMENT PRIMARY KEY,          
    nome VARCHAR(100) NOT NULL,                
    descrizione TEXT,                           
    id_utente INT,                              
    data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  
    FOREIGN KEY (id_utente) REFERENCES utenti(id) ON DELETE CASCADE  
);
