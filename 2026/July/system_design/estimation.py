LATENCY_NS = {
    "L1 cache reference": 0.5,
    "L2 cache reference": 7,
    "Main memory reference": 100,
    "Read 4 KB randomly from SSD": 150_000,
    "Round trip within same datacenter": 500_000,
    "Read 1 MB sequentially from HDD": 30_000_000,
    "Send packet CA -> Netherlands -> CA": 150_000_000,
}

BYTES = {
    "1 KB": 2**10,
    "1 MB": 2**20,
    "1 GB": 2**30,
    "1 TB": 2**40,
}


def print_reference_tables():
    print("=== Latency numbers every programmer should know ===")
    for label, ns in LATENCY_NS.items():
        if ns >= 1_000_000:
            print(f"  {label:<40} {ns/1_000_000:>10.1f} ms")
        elif ns >= 1_000:
            print(f"  {label:<40} {ns/1_000:>10.1f} us")
        else:
            print(f"  {label:<40} {ns:>10.1f} ns")
    print()
    print("=== Powers of two ===")
    for label, n in BYTES.items():
        print(f"  {label:<10} = {n:,} bytes")
    print()

# Scenario: estimate load for sync activity

NUM_FARMS = 50_000
ROWS_PER_SYNC = 200
SYNC_WINDOW_HOURS = 4
AVG_ROW_SIZE_BYTES = 250


def estimate_pos_sync_load():
    print("=== Scenario: daily POS sync load ===")
    print(f"  Inputs: {NUM_FARMS:,} farms, {ROWS_PER_SYNC} rows/farm/day, "
          f"sync window = {SYNC_WINDOW_HOURS}h, avg row size = {AVG_ROW_SIZE_BYTES}B\n")

    total_rows_per_day = NUM_FARMS * ROWS_PER_SYNC
    print(f"  total_rows_per_day   = {NUM_FARMS:,} farms * {ROWS_PER_SYNC} rows "
          f"= {total_rows_per_day:,} rows/day")

    total_bytes_per_day = total_rows_per_day * AVG_ROW_SIZE_BYTES
    total_gb_per_day = total_bytes_per_day / BYTES["1 GB"]
    print(f"  total_bytes_per_day  = {total_rows_per_day:,} rows * {AVG_ROW_SIZE_BYTES}B "
          f"= {total_bytes_per_day:,} bytes ({total_gb_per_day:.3f} GB)")

    gb_per_year = total_gb_per_day * 365
    print(f"  storage_per_year     = {total_gb_per_day:.3f} GB/day * 365 "
          f"= {gb_per_year:,.1f} GB/year")

    writes_per_second_peak = total_rows_per_day / (SYNC_WINDOW_HOURS * 3600)
    print(f"  peak_writes_per_sec  = {total_rows_per_day:,} rows / "
          f"({SYNC_WINDOW_HOURS}h * 3600s) = {writes_per_second_peak:,.1f} writes/sec\n")

    print("   ~%.0f writes/sec is well within a single MariaDB" % writes_per_second_peak)
    print("  instance's comfortable range — this number is what tells you")
    print("  sharding would be premature right now, and the real bottleneck")
    print("  is more likely the read side (reports) than the write side.")
    print()
    return {
        "total_rows_per_day": total_rows_per_day,
        "gb_per_year": gb_per_year,
        "peak_writes_per_sec": writes_per_second_peak,
    }


if __name__ == "__main__":
    print_reference_tables()
    estimate_pos_sync_load()
    print("Edit NUM_FARMS / ROWS_PER_SYNC / SYNC_WINDOW_HOURS above and re-run")
    print("to show the group how the estimate moves with the assumptions.")
