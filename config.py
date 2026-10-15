import os
from sqlalchemy import create_engine
import urllib.parse

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class DatabaseConfig:
    def __init__(self):
        # Parametri di connessione letti dalle variabili d'ambiente (.env)
        self.server = os.environ['SERVER_DB']
        self.database = os.environ['DB_ARCA']
        self.username = os.getenv('DB_USER', '')  # vuoto = autenticazione Windows
        self.password = os.getenv('DB_PASSWORD', '')

    def get_connection_string(self):
        if self.username:
            # SQL Server Authentication
            params = urllib.parse.quote_plus(
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={self.server};"
                f"DATABASE={self.database};"
                f"UID={self.username};"
                f"PWD={self.password}"
            )
        else:
            # Windows Authentication
            params = urllib.parse.quote_plus(
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={self.server};"
                f"DATABASE={self.database};"
                f"Trusted_Connection=yes"
            )
        return f"mssql+pyodbc:///?odbc_connect={params}"

    def get_engine(self):
        return create_engine(self.get_connection_string())
