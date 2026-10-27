import pymysql
from pymysql.cursors import DictCursor
from backend.config import Config

def get_connection():
    """
    Establish a connection to the MySQL database.
    Returns a PyMySQL Connection object configured with DictCursor.
    """
    return pymysql.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
        cursorclass=DictCursor,
        autocommit=False
    )

def query_db(sql, args=(), one=False):
    """
    Execute a SELECT query and return results as a list of dictionaries (or a single dict).
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, args)
            results = cursor.fetchall()
            return results[0] if (one and results) else (None if one else results)
    finally:
        conn.close()

def execute_db(sql, args=(), commit=True):
    """
    Execute an INSERT, UPDATE, or DELETE query.
    Returns the lastrowid or affected rows.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, args)
            if commit:
                conn.commit()
            return cursor.lastrowid
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
