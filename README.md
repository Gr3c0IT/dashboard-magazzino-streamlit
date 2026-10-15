# dashboard-magazzino-streamlit

Web app interna per l'analisi di magazzino e vendite, costruita con Streamlit
sul database del gestionale ARCA Evolution, con autenticazione e permessi per
ruolo.

Richiede: database ARCA Evolution (SQL Server).

## Contesto

Strumento sviluppato per le esigenze di un'azienda di distribuzione che usa
ARCA Evolution, pubblicato in forma anonimizzata con l'autorizzazione
dell'azienda.

## Problema

Acquisti, logistica e contabilità avevano bisogno di consultare giacenze,
venduto e ordinato senza accedere al gestionale né scrivere query.

## Soluzione

Un'applicazione web con filtri, grafici ed export in Excel:

- login con `streamlit-authenticator`: utenti, hash bcrypt e ruoli in
  `auth_config.yaml`, chiave del cookie nel `.env`;
- ruoli (`admin`, `manager`, `logistica`, `contabilita`, `acquisti`) associati a
  permessi in `roles_permissions`, che determinano le sezioni visibili;
- sezioni: riepilogo a card, grafici Plotly, analisi mensile per anno,
  pianificazione ordini (mesi di copertura, giacenza, ordinato, impegnato),
  analisi delle vendite per articolo e cliente con griglie AgGrid;
- accesso ai dati concentrato in `database.py`, con query parametriche su
  `MGMov`, `DOTes`, `DORig`, `AR`, `CF`, `LSArticolo` e filtri per magazzino,
  periodo, cliente e articolo.

## Struttura

```
dashboard-magazzino-streamlit/
├── app.py                     applicazione (login, filtri, sezioni)
├── database.py                query su ARCA
├── config.py                  connessione a SQL Server da variabili d'ambiente
├── components.py              componenti UI riutilizzabili
├── generate_password_hash.py  generazione di password e hash bcrypt
├── auth_config.example.yaml   modello della configurazione utenti e ruoli
├── .streamlit/config.toml     configurazione del server Streamlit
├── requirements.txt
└── .env.example
```

## Tecnologie

Python, Streamlit, streamlit-authenticator, streamlit-aggrid, Plotly, pandas,
SQLAlchemy, pyodbc (ODBC Driver 17 for SQL Server), bcrypt, PyYAML.

## Configurazione

1. Installare ODBC Driver 17 for SQL Server e le dipendenze con
   `pip install -r requirements.txt`.
2. Copiare `.env.example` in `.env` e impostare `SERVER_DB`, `DB_ARCA`,
   `DB_USER`, `DB_PASSWORD` (vuoti per l'autenticazione Windows) e
   `AUTH_COOKIE_KEY`.
3. Copiare `auth_config.example.yaml` in `auth_config.yaml`. Per ogni utente
   eseguire `python generate_password_hash.py` e inserire l'hash nel campo
   `password`; la password in chiaro viene scritta in `password_output.txt`.
4. Avviare con `streamlit run app.py`.

Il file `.env` non è versionato, come `auth_config.yaml` e `password_output.txt`.
