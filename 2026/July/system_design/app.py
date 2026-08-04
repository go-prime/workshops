"""
Capstone — URL Shortener (Flask)
=================================
The end-to-end worked example from the primer, built as a real running app
so the "scale it" phase can be demonstrated by literally uncommenting the
caching layer live, rather than described.

Run:
    redis-server --daemonize yes
    python3 app.py
    # then in another terminal:
    curl -X POST localhost:5000/shorten -d "url=https://gopri.me/some/long/report/path"
    curl -L localhost:5000/<code>

Design, matching the workshop's 4 steps:
  1. Use case: shorten a long URL, redirect on lookup
  2. High-level: Flask app -> SQLite (source of truth) -> Redis (cache)
  3. Core components: base62 encoding, collision-free via autoincrement id,
     schema below
  4. Scale it: cache-aside on the read path (this is the part to toggle
     live — see CACHE_ENABLED)
"""

import sqlite3
import string
import time

from flask import Flask, request, redirect, jsonify, g

import redis

app = Flask(__name__)

DB_PATH = "/tmp/urlshortener.db"

# ---------------------------------------------------------------------------
# Toggle this live in the workshop to show "before caching" vs "after"
# ---------------------------------------------------------------------------
CACHE_ENABLED = True
CACHE_TTL_SECONDS = 300

cache = redis.Redis(host="localhost", port=6379, db=1, decode_responses=True)

BASE62_ALPHABET = string.digits + string.ascii_lowercase + string.ascii_uppercase


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            long_url TEXT NOT NULL,
            created_at REAL NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def to_base62(n: int) -> str:
    """Encode an autoincrement id as base62 — this sidesteps hash collisions
    entirely (step 3 in the primer talks through MD5 + collision handling;
    autoincrement + base62 is the simpler cousin worth mentioning here)."""
    if n == 0:
        return BASE62_ALPHABET[0]
    digits = []
    base = len(BASE62_ALPHABET)
    while n:
        n, rem = divmod(n, base)
        digits.append(BASE62_ALPHABET[rem])
    return "".join(reversed(digits))


def from_base62(code: str) -> int:
    base = len(BASE62_ALPHABET)
    n = 0
    for ch in code:
        n = n * base + BASE62_ALPHABET.index(ch)
    return n


# ---------------------------------------------------------------------------
# Security note (see security_demo.py for the vulnerable version) — every
# query below uses a parameterized placeholder (?), never string formatting.
# ---------------------------------------------------------------------------

@app.route("/shorten", methods=["POST"])
def shorten():
    long_url = request.form.get("url") or (request.json or {}).get("url")
    if not long_url:
        return jsonify({"error": "missing 'url'"}), 400

    db = get_db()
    cur = db.execute(
        "INSERT INTO urls (long_url, created_at) VALUES (?, ?)",
        (long_url, time.time()),
    )
    db.commit()
    code = to_base62(cur.lastrowid)

    if CACHE_ENABLED:
        cache.set(f"short:{code}", long_url, ex=CACHE_TTL_SECONDS)

    return jsonify({"code": code, "short_url": f"/{code}", "long_url": long_url})


@app.route("/<code>")
def resolve(code):
    lookup_start = time.perf_counter()
    source = "cache"

    long_url = None
    if CACHE_ENABLED:
        long_url = cache.get(f"short:{code}")

    if long_url is None:
        source = "database"
        row_id = from_base62(code)
        db = get_db()
        row = db.execute(
            "SELECT long_url FROM urls WHERE id = ?", (row_id,)
        ).fetchone()
        if row is None:
            return jsonify({"error": "not found"}), 404
        long_url = row["long_url"]
        if CACHE_ENABLED:
            cache.set(f"short:{code}", long_url, ex=CACHE_TTL_SECONDS)

    elapsed_ms = (time.perf_counter() - lookup_start) * 1000
    app.logger.info(f"resolve({code}) served from {source} in {elapsed_ms:.2f}ms")
    return redirect(long_url, code=302)


@app.route("/stats/<code>")
def stats(code):
    """Not in the original 4 REST verbs discussion, but a useful example of
    a read that deliberately bypasses cache — click analytics need to be
    correct, not fast."""
    row_id = from_base62(code)
    db = get_db()
    row = db.execute(
        "SELECT long_url, created_at FROM urls WHERE id = ?", (row_id,)
    ).fetchone()
    if row is None:
        return jsonify({"error": "not found"}), 404
    return jsonify({"code": code, "long_url": row["long_url"], "created_at": row["created_at"]})


if __name__ == "__main__":
    init_db()
    print(f"CACHE_ENABLED = {CACHE_ENABLED}  (flip this constant to demo the difference live)")
    app.run(debug=True, port=5000)
