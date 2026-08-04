"""
Database Scaling — Live Demo
=============================
Three self-contained demos, each runnable independently:

    python3 db_scaling_demo.py sharding
    python3 db_scaling_demo.py replication
    python3 db_scaling_demo.py denormalization

Everything runs against local SQLite files/in-memory DBs, so there's no
infra to set up beyond Python itself.
"""

import sqlite3
import sys
import time
import os
import tempfile

# ---------------------------------------------------------------------------
# 1. SHARDING — route rows to one of N databases by a shard key
# ---------------------------------------------------------------------------
SHARD_COUNT = 4
SHARD_DIR = os.path.join(tempfile.gettempdir(), "shards")


UNSHARDED_PATH = os.path.join(tempfile.gettempdir(), "gl_entries_unsharded.db")


def shard_for(company_id: int) -> int:
    """here we shard GL Entries by company_id % SHARD_COUNT."""
    return company_id % SHARD_COUNT


def shard_path(shard_id: int) -> str:
    return f"{SHARD_DIR}/gl_entries_shard_{shard_id}.db"


def _build_unsharded_source():
    """Step 1: one ordinary database, the way it would exist before you'd
    ever decided to shard it. companies: 1=Polaris, 2=Beatrice,
    3=Glenara Estates (plus a few more to show distribution across shards)."""
    if os.path.exists(UNSHARDED_PATH):
        os.remove(UNSHARDED_PATH)
    conn = sqlite3.connect(UNSHARDED_PATH)
    conn.execute(
        "CREATE TABLE gl_entries (id INTEGER PRIMARY KEY, company_id INT, account TEXT, amount REAL)"
    )
    rows = [
        (1, "Sales", 1000.0), (1, "COGS", 400.0),
        (2, "Sales", 2200.0), (2, "COGS", 900.0),
        (3, "Sales", 1750.0), (3, "COGS", 600.0),
        (4, "Sales", 3100.0),
        (5, "Sales", 1450.0), (5, "COGS", 500.0),
        (6, "Sales", 2900.0),
        (7, "Sales", 1120.0), (7, "COGS", 300.0),
        (8, "Sales", 1980.0),
    ]
    conn.executemany(
        "INSERT INTO gl_entries (company_id, account, amount) VALUES (?, ?, ?)",
        rows,
    )
    conn.commit()
    conn.close()
    return len(rows)


def demo_sharding():
    print("=== SHARDING: GL Entries routed by company_id ===\n")

    row_count = _build_unsharded_source()
    print(f"  Step 1 — starting point: ONE database, {row_count} rows, "
          f"8 companies, no sharding yet.")
    print(f"  ({UNSHARDED_PATH})\n")

    print("  Step 2 — physically splitting it: reading every row from the")
    print("  source DB and inserting each one into the shard file that")
    print(f"  company_id % {SHARD_COUNT} points to:\n")

    os.makedirs(SHARD_DIR, exist_ok=True)
    for shard_id in range(SHARD_COUNT):
        path = shard_path(shard_id)
        if os.path.exists(path):
            os.remove(path)
        conn = sqlite3.connect(path)
        conn.execute(
            "CREATE TABLE gl_entries (id INTEGER PRIMARY KEY, company_id INT, account TEXT, amount REAL)"
        )
        conn.commit()
        conn.close()

    source = sqlite3.connect(UNSHARDED_PATH)
    for row in source.execute("SELECT id, company_id, account, amount FROM gl_entries"):
        _id, company_id, account, amount = row
        shard_id = shard_for(company_id)
        conn = sqlite3.connect(shard_path(shard_id))
        conn.execute(
            "INSERT INTO gl_entries (id, company_id, account, amount) VALUES (?, ?, ?, ?)",
            row,
        )
        conn.commit()
        conn.close()
        print(f"    row id={_id} company_id={company_id}  ->  shard {shard_id}")
    source.close()

    print("\n  Step 3 — physically examine each shard file's actual contents")
    print("  (this is the part worth pausing on — these are now four")
    print("  completely independent SQLite files on disk):\n")
    for shard_id in range(SHARD_COUNT):
        path = shard_path(shard_id)
        conn = sqlite3.connect(path)
        rows = conn.execute("SELECT id, company_id, account, amount FROM gl_entries").fetchall()
        conn.close()
        print(f"  {path}")
        if rows:
            for r in rows:
                print(f"      {r}")
        else:
            print("      (empty)")
    print()
    print("  Try it yourself live in a second terminal, on the real file:")
    print(f"    sqlite3 {shard_path(1)} \"SELECT * FROM gl_entries;\"")

    print("\n A query for company_id=3 only ever touches")
    print("  shard 3 — the other three shards aren't scanned at all. That's")
    print("  the payoff. The cost: 'sum this account across ALL companies'")
    print("  now means querying every shard and merging in application code.")

    # Prove the cross-shard cost concretely
    print("\n  Cross-shard aggregate query (has to hit every shard):")
    total = 0.0
    start = time.perf_counter()
    for shard_id in range(SHARD_COUNT):
        conn = sqlite3.connect(shard_path(shard_id))
        cur = conn.execute("SELECT COALESCE(SUM(amount), 0) FROM gl_entries")
        total += cur.fetchone()[0]
        conn.close()
    elapsed_ms = (time.perf_counter() - start) * 1000
    print(f"    -> total={total} across {SHARD_COUNT} shards in {elapsed_ms:.2f} ms")


# ---------------------------------------------------------------------------
# 2. REPLICATION — one master (writes), one read replica (reads only)
# ---------------------------------------------------------------------------
MASTER_PATH = os.path.join(tempfile.gettempdir(), "master.db")
REPLICA_PATH = os.path.join(tempfile.gettempdir(), "replica.db")


def demo_replication():
    print("=== MASTER-SLAVE REPLICATION (simplified) ===\n")
    for path in (MASTER_PATH, REPLICA_PATH):
        if os.path.exists(path):
            os.remove(path)

    master = sqlite3.connect(MASTER_PATH)
    master.execute("CREATE TABLE delivery_notes (id INTEGER PRIMARY KEY, farm TEXT, crop TEXT)")
    master.commit()

    print("  Write path — only the master accepts writes:")
    for farm, crop in [("Farm A", "Maize"), ("Farm B", "Soya"), ("Farm C", "Wheat")]:
        master.execute("INSERT INTO delivery_notes (farm, crop) VALUES (?, ?)", (farm, crop))
        print(f"    master <- INSERT {farm}, {crop}")
    master.commit()

    print("\n  Replicating master -> replica (in real systems: async binlog")
    print("  streaming; here, a simple copy to make the split visible):")
    with sqlite3.connect(REPLICA_PATH) as replica:
        rows = master.execute("SELECT id, farm, crop FROM delivery_notes").fetchall()
        replica.execute("CREATE TABLE delivery_notes (id INTEGER PRIMARY KEY, farm TEXT, crop TEXT)")
        replica.executemany("INSERT INTO delivery_notes VALUES (?, ?, ?)", rows)
        replica.commit()
    print(f"    replicated {len(rows)} rows")

    print("\n  Read path — reports/dashboards hit the REPLICA, not the master:")
    with sqlite3.connect(REPLICA_PATH) as replica:
        for row in replica.execute("SELECT farm, crop FROM delivery_notes"):
            print(f"    replica -> {row}")

    print("\n  if the master goes down, the replica can keep")
    print("  serving reads (read-only mode) until a new master is promoted.")
    print("  This is the exact trade-off behind separating your reporting")
    print("  queries (Gross Profit report, COGS queries) from the write path.")

    master.close()


# ---------------------------------------------------------------------------
# 3. DENORMALIZATION — join query vs. flattened table, timed at scale
# ---------------------------------------------------------------------------
def demo_denormalization(row_count=20000):
    print(f"=== DENORMALIZATION: join vs. flat table ({row_count:,} rows) ===\n")
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()

    # Normalized: delivery_note references farm and crop by id, requiring joins
    cur.execute("CREATE TABLE farms (id INTEGER PRIMARY KEY, name TEXT)")
    cur.execute("CREATE TABLE crops (id INTEGER PRIMARY KEY, name TEXT)")
    cur.execute("""
        CREATE TABLE delivery_notes_normalized (
            id INTEGER PRIMARY KEY, farm_id INT, crop_id INT, quantity REAL
        )
    """)

    # Denormalized: farm/crop names duplicated directly onto each row
    cur.execute("""
        CREATE TABLE delivery_notes_flat (
            id INTEGER PRIMARY KEY, farm_name TEXT, crop_name TEXT, quantity REAL
        )
    """)

    farms = [(i, f"Farm {i}") for i in range(1, 21)]
    crops = [(i, f"Crop {i}") for i in range(1, 6)]
    cur.executemany("INSERT INTO farms VALUES (?, ?)", farms)
    cur.executemany("INSERT INTO crops VALUES (?, ?)", crops)

    import random
    normalized_rows, flat_rows = [], []
    for i in range(row_count):
        farm_id = random.randint(1, 20)
        crop_id = random.randint(1, 5)
        qty = round(random.uniform(1, 500), 2)
        normalized_rows.append((farm_id, crop_id, qty))
        flat_rows.append((f"Farm {farm_id}", f"Crop {crop_id}", qty))

    cur.executemany(
        "INSERT INTO delivery_notes_normalized (farm_id, crop_id, quantity) VALUES (?, ?, ?)",
        normalized_rows,
    )
    cur.executemany(
        "INSERT INTO delivery_notes_flat (farm_name, crop_name, quantity) VALUES (?, ?, ?)",
        flat_rows,
    )
    conn.commit()

    print("  Query: total quantity by farm name, normalized (requires JOIN):")
    start = time.perf_counter()
    cur.execute("""
        SELECT f.name, SUM(dn.quantity)
        FROM delivery_notes_normalized dn
        JOIN farms f ON f.id = dn.farm_id
        GROUP BY f.name
    """)
    cur.fetchall()
    normalized_ms = (time.perf_counter() - start) * 1000
    print(f"    -> {normalized_ms:.2f} ms")

    print("\n  Same query, denormalized (flat table, no JOIN):")
    start = time.perf_counter()
    cur.execute("""
        SELECT farm_name, SUM(quantity)
        FROM delivery_notes_flat
        GROUP BY farm_name
    """)
    cur.fetchall()
    flat_ms = (time.perf_counter() - start) * 1000
    print(f"    -> {flat_ms:.2f} ms")

    print(f"\n Denormalized was {normalized_ms / flat_ms:.1f}x faster on")
    print("  this read, at the cost of storing farm_name/crop_name redundantly")
    print("  on every row — and now a farm rename means updating every row,")
    print("  not one.")

    conn.close()


if __name__ == "__main__":
    demos = {
        "sharding": demo_sharding,
        "replication": demo_replication,
        "denormalization": demo_denormalization,
    }
    choice = sys.argv[1] if len(sys.argv) > 1 else None
    if choice not in demos:
        print("Usage: python3 db_scaling_demo.py [sharding|replication|denormalization] [row_count]")
        sys.exit(1)
    if choice == "denormalization" and len(sys.argv) > 2:
        demos[choice](row_count=int(sys.argv[2]))
    else:
        demos[choice]()