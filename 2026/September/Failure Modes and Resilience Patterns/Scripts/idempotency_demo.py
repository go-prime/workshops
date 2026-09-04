"""
Case Study 3 — Live Demo: Idempotency & Optimistic Concurrency
=================================================================
The two patterns from Case Study 3 that don't already have code elsewhere
in this workshop. Backpressure (Version 3 of the case study) is covered
by resilience_demo.py's rate_limiter and bulkhead demos already — no
need to re-demo it here.

    python3 idempotency_demo.py idempotency
    python3 idempotency_demo.py optimistic_concurrency

No external dependencies.
"""

import sys
import time


# ---------------------------------------------------------------------------
# 1. IDEMPOTENCY KEY — Case Study 3, Version 1 -> Version 2
# ---------------------------------------------------------------------------
_orders_db = []          # simulated Sales Order table
_idempotency_cache = {}  # simulated frappe.cache() — key -> stored response


def _create_sales_order(payload):
    """The actual work: create the order, commit it. In real Frappe, this
    is roughly doc.insert() + doc.submit()."""
    order_id = len(_orders_db) + 1
    order = {"order_id": order_id, "item": payload["item"], "qty": payload["qty"]}
    _orders_db.append(order)
    return {"order_id": order_id, "status": "created"}


def submit_without_idempotency(payload):
    """Version 1: naive. Every call creates a new order, no matter why
    the caller is calling it again."""
    return _create_sales_order(payload)


def submit_with_idempotency(payload, idempotency_key):
    """Version 2: check the key before doing any work. A repeat of a key
    we've seen returns the ORIGINAL response instead of creating anything."""
    if idempotency_key in _idempotency_cache:
        print(f"    idempotency key {idempotency_key} already seen -- "
              f"returning stored response, NOT creating a new order")
        return _idempotency_cache[idempotency_key]

    response = _create_sales_order(payload)
    _idempotency_cache[idempotency_key] = response
    return response


def demo_idempotency():
    print("=== IDEMPOTENCY KEY (Case Study 3, V1 -> V2) ===\n")
    payload = {"item": "Fertilizer 50kg", "qty": 3}

    print("  --- Version 1: no idempotency key ---")
    print("  Terminal submits a sale. Connection drops before the 200 OK")
    print("  arrives. Terminal assumes failure and retries the SAME sale:\n")
    _orders_db.clear()
    r1 = submit_without_idempotency(payload)
    print(f"    first call  -> order created: {r1}")
    r2 = submit_without_idempotency(payload)
    print(f"    retry call  -> order created: {r2}")
    print(f"\n    orders table now has {len(_orders_db)} rows for ONE actual sale.")
    print("    That's a duplicate order -- and a double charge to the customer.")

    print("\n  --- Version 2: same scenario, with an idempotency key ---")
    print("  Terminal generates ONE UUID for this logical transaction and")
    print("  sends it on both the original attempt and the retry:\n")
    _orders_db.clear()
    _idempotency_cache.clear()
    key = "term-042-txn-88f1c2"
    r1 = submit_with_idempotency(payload, key)
    print(f"    first call  -> {r1}")
    r2 = submit_with_idempotency(payload, key)
    print(f"    retry call  -> {r2}")
    print(f"\n    orders table now has {len(_orders_db)} row -- exactly one,")
    print("    even though the terminal made two requests. The retry is now")
    print("    provably safe.")


# ---------------------------------------------------------------------------
# 2. OPTIMISTIC CONCURRENCY — Case Study 3, Version 4
# ---------------------------------------------------------------------------
class StaleWriteError(Exception):
    """Stand-in for Frappe's real frappe.TimestampMismatchError."""
    pass


class StockRecord:
    """A tiny model of one stock ledger row, with the same 'modified'
    timestamp check Frappe uses on every document save."""

    def __init__(self, item, qty):
        self.item = item
        self.qty = qty
        self.modified = time.time()

    def sell(self, amount, expected_modified):
        if abs(expected_modified - self.modified) > 1e-9:
            raise StaleWriteError(
                f"'{self.item}' was modified after you read it "
                f"(expected modified={expected_modified:.4f}, actual={self.modified:.4f}). "
                f"Refresh and re-check before selling."
            )
        if self.qty < amount:
            raise ValueError(f"Not enough stock: {self.qty} available, {amount} requested")
        self.qty -= amount
        self.modified = time.time()
        return self.qty


def demo_optimistic_concurrency():
    print("=== OPTIMISTIC CONCURRENCY (Case Study 3, Version 4) ===\n")
    stock = StockRecord("Fertilizer 50kg", qty=1)  # last unit in stock
    print(f"  Starting stock: {stock.qty}x {stock.item} (the last unit)\n")

    print("  Two terminals go offline at the same moment, both reading")
    print("  the current stock state before losing connectivity:")
    terminal_a_read_modified = stock.modified
    terminal_b_read_modified = stock.modified
    print(f"    Terminal A reads: qty={stock.qty}, modified={terminal_a_read_modified:.4f}")
    print(f"    Terminal B reads: qty={stock.qty}, modified={terminal_b_read_modified:.4f}")
    print("    Both terminals independently sell the last unit while offline.\n")

    print("  Connectivity returns. Terminal A syncs first:")
    try:
        new_qty = stock.sell(amount=1, expected_modified=terminal_a_read_modified)
        print(f"    Terminal A's sale ACCEPTED -- stock updated to {new_qty}, "
              f"modified={stock.modified:.4f}")
    except (StaleWriteError, ValueError) as e:
        print(f"    Terminal A's sale REJECTED: {e}")

    print("\n  Terminal B syncs second, still holding its ORIGINAL read:")
    try:
        new_qty = stock.sell(amount=1, expected_modified=terminal_b_read_modified)
        print(f"    Terminal B's sale ACCEPTED -- stock updated to {new_qty}")
    except StaleWriteError as e:
        print(f"    Terminal B's sale REJECTED: {e}")
        print("\n    This is frappe.TimestampMismatchError in a real Frappe app --")
        print("    Terminal B is forced to refresh and see the current qty (0)")
        print("    before it can proceed. Since there's genuinely nothing left")
        print("    to sell, this sale can't be silently approved OR silently")
        print("    dropped -- it needs to go to a human: refund, apologize,")
        print("    or offer a backorder. That's the reconciliation queue.")


if __name__ == "__main__":
    demos = {
        "idempotency": demo_idempotency,
        "optimistic_concurrency": demo_optimistic_concurrency,
    }
    choice = sys.argv[1] if len(sys.argv) > 1 else None
    if choice not in demos:
        print("Usage: python3 idempotency_demo.py [idempotency|optimistic_concurrency]")
        sys.exit(1)
    demos[choice]()
