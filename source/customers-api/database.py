import os
import psycopg2
from psycopg2.extras import RealDictCursor

def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "postgres"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "cafeboreal"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres"),
        cursor_factory=RealDictCursor
    )

# Clave de cifrado - viene del Secret de Kubernetes (256 bits)
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "clave-de-desarrollo-cambiar-en-produccion")
