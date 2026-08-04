"""
Caching Strategies — Live Demo
==============================
Run each function live during the workshop and read the printed timings out
loud. Requires a real Redis instance running on localhost:6379.

    redis-server --daemonize yes
    python3 caching_demo.py

The "database" is a plain dict with an artificial 200ms delay bolted on,
standing in for a real round trip to MariaDB/Postgres. That delay is what
makes the difference between patterns visible on a stopwatch instead of
just in theory.
"""

import time
import threading
import queue

import redis

r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

# ---------------------------------------------------------------------------
# Simulated "database" — a dict with a fake 200ms network/disk round trip
# ---------------------------------------------------------------------------
DB_LATENCY_SECONDS = 0.2
_fake_db = {
    "user:1": "Tino - Polaris - Branch A",
    "user:2": "Chido - Beatrice - Branch B",
    "user:3": "Farai - Glenara Estates - Branch C",
}


def slow_db_read(key):
    time.sleep(DB_LATENCY_SECONDS)
    return _fake_db.get(key)


def slow_db_write(key, value):
    time.sleep(DB_LATENCY_SECONDS)
    _fake_db[key] = value


def timed(label, fn, *args):
    start = time.perf_counter()
    result = fn(*args)
    elapsed_ms = (time.perf_counter() - start) * 1000
    print(f"    -> {label}: {elapsed_ms:6.1f} ms   result={result}")
    return result


# CACHE-ASIDE — checks cache, falls back to DB, populates cache itself

def get_user_cache_aside(user_id):
    key = f"user:{user_id}"
    cached = r.get(key)
    if cached is not None:
        return cached
    value = slow_db_read(key)
    if value is not None:
        r.set(key, value, ex=60)
    return value


def demo_cache_aside():
    print("\n=== CACHE-ASIDE ===")
    r.delete("user:1")
    print("  First call (cold cache — hits the DB):")
    timed("get_user_cache_aside(1)", get_user_cache_aside, 1)
    print("  Second call (warm cache — skips the DB):")
    timed("get_user_cache_aside(1)", get_user_cache_aside, 1)
    print("  3 trips on a miss (check cache, hit DB, populate")
    print("  cache). Good fit when reads vastly outnumber writes and some")
    print("  staleness (up to the TTL) is fine.")


# 2. WRITE-THROUGH — write goes to DB and cache together, synchronously
# ---------------------------------------------------------------------------
def set_user_write_through(user_id, value):
    key = f"user:{user_id}"
    slow_db_write(key, value)
    r.set(key, value, ex=60)


def demo_write_through():
    print("\n=== WRITE-THROUGH ===")
    print("  Write (pays the DB cost up front):")
    timed("set_user_write_through(1, ...)", set_user_write_through, 1, "Tino - UPDATED")
    print("  Immediate read after write (always fresh, no cache miss):")
    timed("get_user_cache_aside(1)", get_user_cache_aside, 1)
    print("  writes are slower, but reads are never stale.")
    print("  Good fit for the voided-order docstatus case — staleness there")
    print("  is the thing you can't afford.")


# ---------------------------------------------------------------------------
# 3. WRITE-BEHIND (write-back) — cache updates immediately, DB write is async
# ---------------------------------------------------------------------------
_write_queue = queue.Queue()


def _write_behind_worker():
    while True:
        key, value = _write_queue.get()
        slow_db_write(key, value)
        print(f"       (async worker) flushed {key} to DB")


threading.Thread(target=_write_behind_worker, daemon=True).start()


def set_user_write_behind(user_id, value):
    key = f"user:{user_id}"
    r.set(key, value, ex=60)
    _write_queue.put((key, value))


def demo_write_behind():
    print("\n=== WRITE-BEHIND ===")
    print("  Write (returns immediately, DB write queued in background):")
    timed("set_user_write_behind(1, ...)", set_user_write_behind, 1, "Tino - QUEUED-WRITE")
    print("   fastest writes of the four patterns, but if the")
    print("  cache dies before the queue flushes, that write is gone.")
    time.sleep(DB_LATENCY_SECONDS + 0.05)  # let the async worker finish before demo moves on


# ---------------------------------------------------------------------------
# 4. REFRESH-AHEAD — proactively refresh a hot key just before it expires
# ---------------------------------------------------------------------------
def get_user_refresh_ahead(user_id, ttl=6, refresh_window=3):
    key = f"user:{user_id}"
    value = r.get(key)
    ttl_remaining = r.ttl(key)

    if value is None:
        value = slow_db_read(key)
        r.set(key, value, ex=ttl)
        return value

    if 0 < ttl_remaining < refresh_window:
        print("       (background) TTL about to expire — refreshing early")
        threading.Thread(
            target=lambda: r.set(key, slow_db_read(key), ex=ttl)
        ).start()

    return value


def demo_refresh_ahead():
    print("\n=== REFRESH-AHEAD ===")
    r.delete("user:2")
    print("  First call (cold — hits DB, sets a short 6s TTL):")
    timed("get_user_refresh_ahead(2)", get_user_refresh_ahead, 2)
    print("  Waiting until we're inside the refresh window...")
    time.sleep(4)
    print("  Call inside refresh window (returns cached value immediately,")
    print("  but kicks off a background refresh so it never goes cold):")
    timed("get_user_refresh_ahead(2)", get_user_refresh_ahead, 2)
    print("  only pays off when access is predictable — a")
    print("  report that's reliably pulled every morning, for example.")


if __name__ == "__main__":
    print("Caching Strategies — Live Demo")
    print("Make sure redis-server is running on localhost:6379.\n")
    demo_cache_aside()
    demo_write_through()
    demo_write_behind()
    demo_refresh_ahead()
    print("\nDone. Re-run any single demo_*() function from a REPL to replay it.")
