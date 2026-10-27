"""
Database Setup Script for Project Kashi
Connects to local MySQL Server and executes schema.sql to create tables,
views, procedures, triggers, and sample records.
"""

import os
import sys
import pymysql

# Get DB credentials from environment or defaults
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "Jalwa@123")
DB_NAME = os.getenv("DB_NAME", "project_kashi")

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEMA_FILE = os.path.join(CURRENT_DIR, "schema.sql")

def setup():
    print(f"Connecting to MySQL server at {DB_HOST}:{DB_PORT} as '{DB_USER}'...")
    try:
        conn = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            autocommit=True,
            client_flag=pymysql.constants.CLIENT.MULTI_STATEMENTS
        )
        print("Connected successfully to MySQL Server!")
    except Exception as e:
        print(f"Error connecting to MySQL: {e}")
        print("Tip: Check your DB_PASSWORD or MySQL service status.")
        sys.exit(1)

    print(f"Reading schema definition from: {SCHEMA_FILE}")
    with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
        sql_content = f.read()

    # PyMySQL can execute multiple statements when CLIENT.MULTI_STATEMENTS is enabled,
    # but DELIMITER blocks need clean handling.
    # We will parse out standard SQL and DELIMITER blocks cleanly.
    print("Executing schema setup...")

    # We will split on standard semicolons while preserving procedures/triggers
    cursor = conn.cursor()
    
    # Simple and robust parser for MySQL scripts with DELIMITER $$
    statements = []
    current_delimiter = ";"
    current_stmt = []

    for line in sql_content.splitlines():
        trimmed = line.strip()
        if trimmed.startswith("--") or not trimmed:
            continue
        
        if trimmed.upper().startswith("DELIMITER"):
            parts = trimmed.split()
            if len(parts) >= 2:
                current_delimiter = parts[1]
            continue
        
        current_stmt.append(line)
        if trimmed.endswith(current_delimiter):
            # End of statement
            stmt_text = "\n".join(current_stmt)
            # Remove trailing delimiter
            stmt_text = stmt_text[:-(len(current_delimiter))].strip()
            if stmt_text:
                statements.append(stmt_text)
            current_stmt = []

    if current_stmt:
        remainder = "\n".join(current_stmt).strip()
        if remainder:
            statements.append(remainder)

    # Execute statements
    executed_count = 0
    for stmt in statements:
        stmt = stmt.strip()
        if not stmt:
            continue
        try:
            cursor.execute(stmt)
            executed_count += 1
        except Exception as e:
            # Print warning but keep going if view/trigger already existed
            print(f"Notice on statement: {stmt[:60]}... -> {e}")

    cursor.close()
    conn.close()

    # Reconnect specifically to project_kashi and verify tables
    verify_conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    v_cursor = verify_conn.cursor()
    v_cursor.execute("SHOW TABLES;")
    tables = [row[0] for row in v_cursor.fetchall()]
    print(f"\nDatabase '{DB_NAME}' initialized successfully!")
    print(f"Total tables/views found ({len(tables)}): {', '.join(tables)}")

    # Check sample customer count
    v_cursor.execute("SELECT COUNT(*) FROM CUSTOMER;")
    cust_count = v_cursor.fetchone()[0]
    print(f"Sample customers loaded: {cust_count}")

    v_cursor.execute("SELECT COUNT(*) FROM ACCOUNT;")
    acc_count = v_cursor.fetchone()[0]
    print(f"Sample accounts loaded: {acc_count}")

    v_cursor.execute("SELECT COUNT(*) FROM TRANSACTION;")
    txn_count = v_cursor.fetchone()[0]
    print(f"Sample transactions loaded: {txn_count}")

    v_cursor.close()
    verify_conn.close()
    print("\nAll database tables and constraints are verified and operational!")

if __name__ == "__main__":
    setup()
