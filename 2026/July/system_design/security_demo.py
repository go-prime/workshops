"""
Security Pass — Live Demo
==========================
Two versions of the same lookup against an in-memory SQLite table, run
side by side: one built with string formatting (vulnerable), one built
with a parameterized query (safe). Run this right after the capstone so
the "attack" targets the exact kind of endpoint just built.

    python3 security_demo.py
"""

import sqlite3

conn = sqlite3.connect(":memory:")
conn.execute("""
    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        username TEXT,
        password TEXT,
        is_admin INTEGER
    )
""")
conn.executemany(
    "INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)",
    [
        ("tino", "correct-password", 0),
        ("admin", "super-secret", 1),
    ],
)
conn.commit()


# ---------------------------------------------------------------------------
# VULNERABLE — user input is spliced directly into the SQL string
# ---------------------------------------------------------------------------
def login_vulnerable(username: str, password: str):
    query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
    print(f"    [vulnerable] executing: {query}")
    cur = conn.execute(query)
    return cur.fetchone()


# ---------------------------------------------------------------------------
# SAFE — the exact same query, but with parameter placeholders
# ---------------------------------------------------------------------------
def login_safe(username: str, password: str):
    query = "SELECT * FROM users WHERE username = ? AND password = ?"
    print(f"    [safe] executing: {query}  params=({username!r}, {password!r})")
    cur = conn.execute(query, (username, password))
    return cur.fetchone()


def demo():
    print("=== Legitimate login, both versions behave the same ===")
    print("  vulnerable:", login_vulnerable("tino", "correct-password"))
    print("  safe:      ", login_safe("tino", "correct-password"))

    print("\n=== Attack: classic ' OR '1'='1' -- payload, no password needed ===")
    attack_username = "' OR '1'='1' -- "
    attack_password = "anything"

    print("\n  Against the VULNERABLE version:")
    result = login_vulnerable(attack_username, attack_password)
    print(f"    -> logged in as: {result}")
    print("    (the string splice turned the WHERE clause into an always-true")
    print("     condition — this returns the FIRST row in the table, which")
    print("     happens to be an account the attacker never had credentials for)")

    print("\n  Against the SAFE version:")
    result = login_safe(attack_username, attack_password)
    print(f"    -> logged in as: {result}")
    print("    (the placeholder treats the entire payload as a literal string")
    print("     to match against — no row has that as a literal username, so")
    print("     nothing matches)")

    print("\nTalking point: this is the exact difference between the capstone's")
    print("parameterized queries (db.execute(\"... WHERE id = ?\", (row_id,)))")
    print("and what would happen if we'd built that query with an f-string.")


if __name__ == "__main__":
    demo()
