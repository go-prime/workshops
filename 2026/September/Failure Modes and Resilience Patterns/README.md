
# Failure Modes & Resilience Patterns

  

When a system communicates to something outside its own process (the FOEP dispatch API, a POS terminal, a mobile app on a slow rural connection) — it's assuming the readiness and availability of something that can fail on its own schedule, for its own reasons, with no guarantee of telling us cleanly when it happens. API calls that half-succeed, expected responses that never register, a retry that posted twice can result in those bugs that are the trickiest to trace. The aim for all of our systems should be that they fail predictably, recover gracefully and avoid cascading failures. This WORKSHiP covers the patterns for handling that honestly, where Frappe already does the work for us, and where it doesn't.

## Failure Modes
### Transient Failure
Something temporarily goes offline or is disrupted.
```
HTTP 503
Temporary network interruption
Database connection reset
Redis restarting
```
### Persistent Failure
The dependency is unavailable for an in-determinant period.
  ```
  Database server offline
Wrong API credentials
External service down for 2 hours
  ```
  ### Slow Failure
  The process is technically working, but is extremely slow
  ```
  Normal API response: 100ms
Degraded API response: 45 seconds
  ```
  ### Overload
  The service is working but is inundated with requests to process.
  ```
  Queued up requests now all arriving at the same time
  Thousands of Stock Ledger Entries being processed.
  Big reports
  
  ```
  ### Cascading Failure
  One failing service consumes all the available system resources, affecting other parallel services. The original issue was external, the final failure is internal.
  ```
  External Tax API becomes slow
        ↓
ERPNext requests wait
        ↓
Gunicorn workers become occupied
        ↓
More requests queue
        ↓
Users retry
        ↓
More requests arrive
        ↓
Database connections remain open
        ↓
Entire ERP becomes slow
  ```

## ERPNext

  

Not a distribute system in the classic sense. ERPNext core is a single Python application talking to a single MariaDB instance. Not a set of independent services calling each other over a network. Concepts like (circuit breakers, bulkheads) are better suited for the latter.

  

While not a distributed system, in some of our projects specific calls cross a boundary where the other side can fail independently, over a network neither side controls.

  

-  **Outbound** — Frappe calling FOEP. Frappe is the client here.

-  **Inbound** — mobile apps and POS terminals calling Frappe. Frappe is now the thing that might be slow or unreachable.

  

These are different problems wearing the same four pattern names. A Mobile App that retries a submission because it didn't receive a response, hitting an endpoint that isn't idempotent, leading to syncing issues — which is exactly why idempotency, not circuit breakers, ends up being the centerpiece of the inbound side, not an afterthought to it.

  

## Frappe Provisions
Before reaching for custom code, it's worth knowing what's already covered:

  

| Pattern | Frappe provides out of the box | What we still need to add | Where it applies |
|---|---|---|---|
| Rate Limiting | Via `site_config.json` (`rate_limit: {limit, window}`), measured in cumulative request time, returns HTTP 429 when limit breach | Nothing for inbound. For protecting FOEP from *us*, we still need our own outbound limiter | Inbound: covered. Outbound: supplement |
| Caching | `frappe.cache()`, `get_cached_doc()`, `@redis_cache()` | Nothing structurally — but it reduces how often the other patterns get exercised at all | Both |
| Optimistic Concurrency | `frappe.TimestampMismatchError` on a stale `modified` field | Nothing for single-document conflicts. Multi-terminal *offline* conflicts still need a reconciliation step on top, covered in the case study below | Inbound |
| Bulkhead (isolation) | Partial — custom RQ queues with their own worker count are supported via `common_site_config.json` | The queue exists as infrastructure; isolation only happens once we deliberately route API Integrations traffic onto a dedicated queue instead of `default` | Both — must be configured, not automatic |
| Idempotency | No | Yes, fully custom — an idempotency-key pattern backed by `frappe.cache()` | Inbound — POS/mobile submissions |
| Retry (outbound) | No built-in wrapper for arbitrary external calls | Yes — a `urllib3` Retry adapter on our `requests.Session` for FOEP calls | Outbound — FOEP |
| Circuit Breaker | No | Yes, in both directions | Both |

  

Frappe covers a lot of the inbound volume scenarios and simple conflict issues. Everything to do with *correctness under retry* — idempotency specifically — is entirely on us.

  

## The Four Patterns

  

### Retry

  

The fairly common and least complicated pattern. Upon failure, wait and try again. Each waiting period might need to get longer than the last (exponential backoff), plus a small random offset so that simultaneous client failures at the same time don't retry at the same time and producing a spike that might have caused the initial failure — the same idea as the TTL jitter used against cache stampedes (System Design Workshop). `resilience_demo.py`

  

### Circuit Breaker

  

If a dependency is down for a prolonged period. The retry pattern will fall short. Retrying will not help and will just pile on to something already struggling. Compounded further if you are queuing requests in a message broker. A circuit breaker tracks recent failures and, once they cross a threshold, stops even trying. Forces immediate failures, without touching the network, for a fixed cooldown period. After that cooldown, we make a probing call to check if conditions have changed, if it succeeds, the circuit closes and normal traffic resumes; if it fails, the cooldown starts again.

  Production circuit breakers more often use a failure *rate* over a sliding window — resilience4j, a widely used Java resilience library, defaults to opening once 50% of calls in a rolling window have failed. Both are the same idea; the rate-based version is just less sensitive to a handful of failures during genuinely low traffic.
```
          Success
             │
             ▼
        ┌────────┐
        │ CLOSED │
        └────────┘
             │
     Too many failures
             │
             ▼
        ┌────────┐
        │  OPEN  │
        └────────┘
             │
    Wait period expires
             │
             ▼
       ┌───────────┐
       │ HALF-OPEN │
       └───────────┘
             │
       ┌─────┴─────┐
       │           │
    Success     Failure
       │           │
       ▼           ▼
    CLOSED       OPEN
```

### Rate Limiter

  

If circuit breaker protects systems from a dependency struggling over a given period, a rate limiter protects by capping how many outbound can we made over a given window, regardless of whether the dependency is healthy or not. The demo implements this as a token bucket: a small reserve of "tokens" that refill steadily over time, each outbound call spending one. Run a burst of requests and the first few succeed instantly; the rest are rejected until the bucket refills. The point is to lessen the chances of causing the failure in the first place.

  

### Bulkhead

  

A concept derived from ship design — a bulkhead is a partition that keeps flooding in one compartment from sinking the whole vessel. Involves isolating parts of an application into pools or compartments so that failure of one component will not cascade to other components. Essentially, restricting failure to small siloed compartments will stop the whole ship from sinking. 

```
                         Application
                              │
               ┌──────────────┼──────────────┐
               │              │              │
               ▼              ▼              ▼
         Critical Work    Reporting    External API
          30 threads     10 threads     10 threads
```

#### Frappe ERPnext
A documented bulkhead pattern exists in Frappe. It explicitly supports custom queues and lets you configure a dedicated number of background workers for them. In `common-site-config`.
```
{
    "workers": {
        "fiscalization": {
            "timeout": 5000,
            "background_workers": 2
        }
    }
}
```
How Frappe's queues implement this

```
                           Frappe
                              │
               ┌──────────────┼──────────────┐
               │              │              │
               ▼              ▼              ▼
            default         long       fiscalization
             Queue          Queue          Queue
               │              │              │
            Workers        Workers        Workers
               │              │              │
          Normal Jobs    Heavy Jobs    2 Workers Max
```

#### If fiscalisation service degrades, the pair of workers will be blocked. With the other workers unaffected.
  

## Implementing These in Frappe

  

The demo patterns may be a little too abstracted to be used directly into a system like Frappe. A Frappe site typically runs multiple gunicorn worker processes, each with its own separate memory.

  

**Retry** is an exception — a retry loop lives and dies within a single request, so there's no shared-state problem, and the idiomatic implementation is `urllib3`'s built-in `Retry` adapter mounted on a `requests.Session`, rather than a hand-rolled loop.
```Python
import urllib3

http = urllib3.PoolManager()

# Retry 10 times on failures
response = http.request('GET', 'https://httpbin.org', retries=10)

# Disable all retries and redirects
response_no_retry = http.request('GET', 'https://httpbin.org', retries=False)

```

  

**Circuit breaker**  state (`state`, `failure_count`, `opened_at`) moves into `frappe.cache().get_value()` / `set_value()`, keyed so every worker reads and writes the same record. Setting an `expires_in_sec` on that key doubles as a safety net: if something goes wrong and the key is never updated again, the breaker self-heals back to usable after an hour instead of staying stuck open indefinitely.

```Python
import time
import frappe

# Usage call_foep_with_circuit_breaker(lambda: create_dispatch(payload))

CIRCUIT_KEY = "foep_circuit_breaker"
FAILURE_THRESHOLD = 3
RESET_TIMEOUT = 30  # seconds

class CircuitOpenError(Exception):
    pass

def _get_circuit_state():
    return frappe.cache().get_value(CIRCUIT_KEY) or {
        "state": "CLOSED", "failure_count": 0, "opened_at": None
    }

def _set_circuit_state(state):
    # expires_in_sec is a safety net: if this key is never updated again,
    # the breaker self-heals back to usable after an hour instead of
    # staying stuck OPEN forever.
    frappe.cache().set_value(CIRCUIT_KEY, state, expires_in_sec=3600)

def call_foep_with_circuit_breaker(fn):
    circuit = _get_circuit_state()

    if circuit["state"] == "OPEN":
        if time.time() - circuit["opened_at"] >= RESET_TIMEOUT:
            circuit["state"] = "HALF_OPEN"
            _set_circuit_state(circuit)
        else:
            raise CircuitOpenError("FOEP circuit is OPEN — failing fast")

    try:
        result = fn()
        _set_circuit_state({"state": "CLOSED", "failure_count": 0, "opened_at": None})
        return result
    except requests.RequestException:
        circuit["failure_count"] += 1
        if circuit["state"] == "HALF_OPEN" or circuit["failure_count"] >= FAILURE_THRESHOLD:
            circuit["state"] = "OPEN"
            circuit["opened_at"] = time.time()
        _set_circuit_state(circuit)
        raise
```

  



  

**Bulkhead** maps onto infrastructure that already exists: Frappe's RQ queues support custom definitions in `common_site_config.json`, each with its own worker count. Giving FOEP calls a dedicated `foep` queue with two workers, and routing to it with `frappe.enqueue(method, queue="foep", ...)`, produces exactly the same guarantee as the demo's in-process semaphore — just enforced at the infrastructure level instead of inside a single script.

  

## Case Study: Orders From an Offline Terminal

  

We want to deploy 150 terminals. Iterating from the naive version to something workable is a useful way to see all four patterns — plus two things Frappe already gives us — used in the order they'd actually get reached for.

  

**Version 1 - Naive Retry** is the naive case: a terminal submits an Order via the API, Frappe creates it, commits it, and sends back `200 OK`. A failure shows up immediately, the connection drops right before that response can be picked up. The terminal cannot determine if the request never reached the server or if the server processed it and the response never came through. So it retries. Frappe, with no memory of having seen this exact submission before, creates a second order and double-charges the customer.

  

**Version 2 - Idem-potency Protection** Closes that gap idem-potency key. the client generates a UUID once per logical transaction and sends it as an `X-Idempotency-Key` header. Frappe side wee checks that key against `frappe.cache()` before calling `doc.insert()` — if it's been seen before, it returns the stored original response instead of creating anything new. Retries are now safe. The internet goes down for two hours, all 150 terminals queue their sales locally, and the moment connectivity returns, all 150 fire their now requests ,correctly packaged with idempotency keys, within the same few seconds. Each request is correct but the gunicorn worker pool and RQ queues are not built to absorb 150 simultaneous requests. This is the same shape as a cache stampede — a burst of held-back demand releasing all at once — just at the connection layer instead of the cache layer.

  

**Version 3 - Rate Limiting** We leverage Frappe's built-in rate limiting server side (accept 300 requests over an hour window) , and having each terminal stagger its own batch of queued submissions client-side (rather than firing all of them in the same instant) reduces the impact of the burst. Requests now arrive at a rate the system can actually absorb. A different problem emerges. Two terminals, both offline for the same two hours, both sold the last unit of the same stock item. Nothing about the request handling was wrong — the underlying data is just genuinely in conflict.

  

**Version 4 - Leverage Frappe Concurrency Protection ** via the `modified` timestamp. When the second terminal's sync tries to update stock based on a value that's since changed, Frappe raises `TimestampMismatchError` rather than silently overwriting it. This will force that sync to re-pull current stock before finalizing. <We need to recheck the details of this and give a more detailed explanation.> Under optimistic concurrency, the system allows multiple records to be created and updated without enforcing hard locks, checking for conflicts happens only at the time of commit. <does frappe do this>

 
  


## Additional Resources
https://docs.frappe.io/framework/user/en/rate-limiting
https://docs.frappe.io/framework/user/en/api/background_jobs
https://github.com/go-prime/health-monitoring/blob/159b4b80abdab1d82b7b7c8eed3938e3bf6b529a/ping_monitor.py#L43-L75
https://github.com/go-prime/farming/blob/94d886db62e2c59829473e1176be857568152d48/farming/farming/api/foep.py#L101
https://github.com/go-prime/erpnext/blob/9552298b0b2c2824e14a5737d42f6c8e42cf5e60/erpnext/stock/doctype/stock_reconciliation/stock_reconciliation.py#L427
