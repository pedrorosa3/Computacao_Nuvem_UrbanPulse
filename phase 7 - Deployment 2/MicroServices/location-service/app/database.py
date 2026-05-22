import psycopg2
import psycopg2.extras
import os

DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "location-db"),
    "port":     int(os.getenv("DB_PORT", 5432)),
    "dbname":   os.getenv("DB_NAME", "location_db"),
    "user":     os.getenv("DB_USER", "admin"),
    "password": os.getenv("DB_PASSWORD", "isqueiro20"),
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def execute_query(query: str, params: tuple = None) -> list[dict]:
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(query, params)
        results = cur.fetchall()
        return [dict(row) for row in results]
    finally:
        conn.close()