"""
Failure Modes & Resilience Patterns — Live Demo
=================================================
Four patterns, demonstrated against a deliberately flaky "FOEP dispatch
API" simulation — standing in for a real third-party call that can fail,
hang, or get hammered with too many concurrent requests.

    python3 resilience_demo.py retry
    python3 resilience_demo.py circuit_breaker
    python3 resilience_demo.py rate_limiter
    python3 resilience_demo.py bulkhead

No external dependencies — pure Python threading/time, so it runs
anywhere the other demos do.
"""

import random
import sys
import threading
import time


# ---------------------------------------------------------------------------
# Simulated flaky FOEP dispatch API
# ---------------------------------------------------------------------------
class FOEPUnavailable(Exception):
    pass


def call_foep_api(fail_rate=0.6, latency=0.05):
    """Simulates a real third-party call: sometimes fails outright,
    otherwise takes a small, real amount of time."""
    time.sleep(latency)
    if random.random() < fail_rate:
        raise FOEPUnavailable("FOEP dispatch endpoint returned 503")
    return {"dispatch_id": random.randint(1000, 9999), "status": "accepted"}


# ---------------------------------------------------------------------------
# 1. RETRY — with exponential backoff + jitter
# ---------------------------------------------------------------------------
def call_with_retry(fn, max_attempts=4, base_delay=0.2):
    for attempt in range(1, max_attempts + 1):
        try:
            result = fn()
            print(f"    attempt {attempt}: SUCCESS -> {result}")
            return result
        except FOEPUnavailable as e:
            if attempt == max_attempts:
                print(f"    attempt {attempt}: FAILED ({e}) -- giving up")
                raise
            delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 0.1)
            print(f"    attempt {attempt}: FAILED ({e}) -- retrying in {delay:.2f}s")
            time.sleep(delay)


def demo_retry():
    print("=== RETRY (exponential backoff + jitter) ===\n")
    print("  Calling the flaky FOEP API with a 60% failure rate:")
    try:
        call_with_retry(lambda: call_foep_api(fail_rate=0.6), max_attempts=5)
    except FOEPUnavailable:
        print("    all attempts exhausted -- this dispatch needs manual review")
    print("\n  Talking point: each retry waits longer than the last (0.2s, 0.4s,")
    print("  0.8s...) so a struggling API gets breathing room instead of being")
    print("  hammered harder while it's already failing. The jitter (+0-0.1s)")
    print("  stops many clients from retrying in lockstep and re-causing the")
    print("  exact spike that caused the failure -- same idea as the TTL jitter")
    print("  from the cache stampede case study.")


# ---------------------------------------------------------------------------
# 2. CIRCUIT BREAKER — fail fast once a dependency looks unhealthy
# ---------------------------------------------------------------------------
class CircuitOpenError(Exception):
    pass


class CircuitBreaker:
    CLOSED, OPEN, HALF_OPEN = "CLOSED", "OPEN", "HALF_OPEN"

    def __init__(self, failure_threshold=3, reset_timeout=2.0):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.state = self.CLOSED
        self.failure_count = 0
        self.opened_at = None

    def call(self, fn):
        if self.state == self.OPEN:
            if time.time() - self.opened_at >= self.reset_timeout:
                self.state = self.HALF_OPEN
                print("    circuit: OPEN -> HALF_OPEN (probing with one call)")
            else:
                raise CircuitOpenError("circuit is OPEN -- failing fast, not calling FOEP")

        try:
            result = fn()
            if self.state == self.HALF_OPEN:
                print("    circuit: probe succeeded -> HALF_OPEN -> CLOSED")
            self.state = self.CLOSED
            self.failure_count = 0
            return result
        except FOEPUnavailable:
            self.failure_count += 1
            if self.state == self.HALF_OPEN or self.failure_count >= self.failure_threshold:
                self.state = self.OPEN
                self.opened_at = time.time()
                print(f"    circuit: -> OPEN (after {self.failure_count} failures, "
                      f"will probe again in {self.reset_timeout}s)")
            raise


def demo_circuit_breaker():
    print("=== CIRCUIT BREAKER ===\n")
    breaker = CircuitBreaker(failure_threshold=3, reset_timeout=2.0)

    print("  Calling a FOEP API that is currently down (100% failure rate):")
    for i in range(1, 6):
        try:
            breaker.call(lambda: call_foep_api(fail_rate=1.0))
        except FOEPUnavailable:
            print(f"    call {i}: FOEP call failed normally")
        except CircuitOpenError as e:
            print(f"    call {i}: {e} (no network call made -- instant)")

    print("\n  Waiting for the reset_timeout so the breaker probes again...")
    time.sleep(2.1)

    print("  FOEP has recovered now (0% failure rate) -- next call is the probe:")
    try:
        breaker.call(lambda: call_foep_api(fail_rate=0.0))
    except FOEPUnavailable:
        pass

    print("\n  Talking point: after 3 failures the breaker stops even trying --")
    print("  calls 4 and 5 above never touched the network, they failed")
    print("  instantly. That's the point: once a dependency is clearly down,")
    print("  retrying it just adds load and makes YOUR request queue back up")
    print("  too. This is what protects the rest of GoPrime if the FOEP API")
    print("  hangs during a dispatch run.")


# ---------------------------------------------------------------------------
# 3. RATE LIMITER — token bucket
# ---------------------------------------------------------------------------
class TokenBucket:
    def __init__(self, capacity=5, refill_rate=1):
        """capacity: max tokens. refill_rate: tokens added per second."""
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()

    def allow(self):
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False


def demo_rate_limiter():
    print("=== RATE LIMITER (token bucket) ===\n")
    bucket = TokenBucket(capacity=3, refill_rate=1)  # 3 burst, 1/sec refill

    print("  Firing 6 dispatch requests back-to-back (bucket capacity = 3):")
    for i in range(1, 7):
        if bucket.allow():
            print(f"    request {i}: ALLOWED -> calling FOEP")
        else:
            print(f"    request {i}: REJECTED -- over the limit, not calling FOEP")

    print("\n  Waiting 2s for the bucket to refill...")
    time.sleep(2)
    print("  Firing 2 more requests:")
    for i in range(7, 9):
        if bucket.allow():
            print(f"    request {i}: ALLOWED -> calling FOEP")
        else:
            print(f"    request {i}: REJECTED")

    print("\n  Talking point: this protects FOEP from US -- if a batch dispatch")
    print("  job ever loops faster than intended, the rate limiter caps our")
    print("  own outbound call rate instead of us finding out the hard way")
    print("  that FOEP has a rate limit of their own.")


# ---------------------------------------------------------------------------
# 4. BULKHEAD — isolate concurrency so one dependency can't starve everything
# ---------------------------------------------------------------------------
def demo_bulkhead():
    print("=== BULKHEAD ===\n")
    max_concurrent = 2
    sem = threading.Semaphore(max_concurrent)
    results = []
    lock = threading.Lock()

    def worker(worker_id):
        acquired_at = time.time()
        with sem:
            wait = time.time() - acquired_at
            with lock:
                results.append((worker_id, wait))
            print(f"    worker {worker_id}: got a slot after waiting {wait:.2f}s -- calling FOEP")
            call_foep_api(fail_rate=0.0, latency=0.5)
            print(f"    worker {worker_id}: done")

    print(f"  6 dispatch jobs arrive at once, but only {max_concurrent} "
          f"concurrent FOEP calls are allowed:\n")
    threads = [threading.Thread(target=worker, args=(i,)) for i in range(1, 7)]
    start = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    elapsed = time.time() - start

    print(f"\n  All 6 jobs finished in {elapsed:.2f}s, {max_concurrent} at a time.")
    print("  : without this limit, 6 simultaneous dispatch jobs")
    print("  would open 6 simultaneous connections to FOEP. With a bulkhead,")
    print("  at most 2 are ever in flight -- a slow or struggling FOEP endpoint")
    print("  can only ever tie up 2 of GoPrime's worker slots, not all of them,")
    print("  so unrelated requests (POS sync, reports) keep moving.")


if __name__ == "__main__":
    demos = {
        "retry": demo_retry,
        "circuit_breaker": demo_circuit_breaker,
        "rate_limiter": demo_rate_limiter,
        "bulkhead": demo_bulkhead,
    }
    choice = sys.argv[1] if len(sys.argv) > 1 else None
    if choice not in demos:
        print("Usage: python3 resilience_demo.py [retry|circuit_breaker|rate_limiter|bulkhead]")
        sys.exit(1)
    demos[choice]()
