import psycopg2
import psycopg2.extras
import os

DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "trip-db"),
    "port":     int(os.getenv("DB_PORT", 5432)),
    "dbname":   os.getenv("DB_NAME", "trip_db"),
    "user":     os.getenv("DB_USER", "admin"),
    "password": os.getenv("DB_PASSWORD"),
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

def execute_write(query: str, params: tuple = None) -> int:
    """Execute INSERT/UPDATE/DELETE and return affected row count."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()

def execute_write_returning(query: str, params: tuple = None) -> dict | None:
    """Execute INSERT/UPDATE with RETURNING clause."""
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(query, params)
        conn.commit()
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()
