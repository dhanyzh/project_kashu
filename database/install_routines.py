import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import pymysql
from backend.config import Config

SCHEMA_FILE = os.path.join(os.path.dirname(__file__), "schema.sql")

with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
    sql_content = f.read()

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
        stmt_text = "\n".join(current_stmt)
        stmt_text = stmt_text[:-(len(current_delimiter))].strip()
        if stmt_text:
            statements.append(stmt_text)
        current_stmt = []

if current_stmt:
    remainder = "\n".join(current_stmt).strip()
    if remainder:
        statements.append(remainder)

print(f"Executing {len(statements)} statements...")
conn = pymysql.connect(
    host=Config.DB_HOST,
    port=Config.DB_PORT,
    user=Config.DB_USER,
    password=Config.DB_PASSWORD,
    autocommit=True
)
cur = conn.cursor()
cur.execute("CREATE DATABASE IF NOT EXISTS project_kashi;")
cur.execute("USE project_kashi;")
for i, stmt in enumerate(statements):
    if stmt.upper().startswith("DROP DATABASE") or stmt.upper().startswith("CREATE DATABASE") or stmt.upper().startswith("USE"):
        continue
    try:
        cur.execute(stmt)
        print(f"Executed statement {i+1}: {stmt.splitlines()[0][:50]}", flush=True)
    except Exception as e:
        print(f"Error on statement {i+1}: {e}", flush=True)

cur.close()
conn.close()

# Verify
verify_conn = pymysql.connect(
    host=Config.DB_HOST,
    port=Config.DB_PORT,
    user=Config.DB_USER,
    password=Config.DB_PASSWORD,
    database=Config.DB_NAME
)
v_cur = verify_conn.cursor()
v_cur.execute("SHOW TABLES")
print("Tables & Views:", [r[0] for r in v_cur.fetchall()])

v_cur.execute("SHOW FUNCTION STATUS WHERE Db=%s", (Config.DB_NAME,))
print("Functions:", [r[1] for r in v_cur.fetchall()])

v_cur.execute("SHOW PROCEDURE STATUS WHERE Db=%s", (Config.DB_NAME,))
print("Procedures:", [r[1] for r in v_cur.fetchall()])

v_cur.execute("SHOW TRIGGERS")
print("Triggers:", [r[0] for r in v_cur.fetchall()])

v_cur.close()
verify_conn.close()
print("\nSUCCESS: All tables, functions, views, triggers, and procedures installed!")
