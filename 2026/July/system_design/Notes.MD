# System Design
Defined best as "the process of developing, expressing, documenting, and communicating the realization of the architecture of the system through a complete set of design characteristics described in a form suitable for implementation. - The Systems Engineering Body of Knowledge (SEBoK)". This workshop will explore some key concepts, best practices and heuristics to employ as we design our solutions. Giving time to thoughtful design and architecture can be taken for granted and not giving it enough time ('kicking the ball down the road') only increases the amount of work and stop-gaps you would need to fix issues that come about as a result of thoughtless design.

In this workshop we will cover some key concepts in design

- Caching Strategies
- DB Scaling
- Coming up with estimates
- Security

## Design Process - Key Steps To Design Problems
This may be a new feature or a scaling decision.

  
1. Come up with use-cases, constraints and assumptions. 
  - Who are the users, and how many are there?
  - What is the read/write ratio?
  - How much data are we handling?
  - What level of availability is required?
  - What level of throughput is required?

2. Sketch a high level design. Layout the main components and their justification.
3. Design Core Components. Select a few components that are most crucial. Specify which caching strategy fits this access pattern, which DB scaling technique fits the expected growth curve.
4. Scale the design - Anticipate and state expected or likely bottlenecks and present solutions. This is where caching, sharding, replication, and de-normalization actually get applied, once step 1's numbers say they're needed rather than assumed upfront.

## Trade Offs
- Performance Vs Scalability
- Latency Vs Throughput
- Availability Versus Consistency


### Case Study 1: A Caching System For A Database
#### User sends query to back-end that he needs to find a social media profile. 
- Version 1 - User sends query, the code checks the cache first, if the profile is found return cache, if not in cache, hit the database, write data into cache, then return it back to the user. Subsequent requests will now read from cached data. 
Drawback - User updates profile and it's written to DB, however the stale data is being returned to the user because cache still holds the value.
- Version 2 - Introduce TTL expiration. Allow cache to live for 5 minutes before it expires. This solves the stale data problem.
Drawback - Is 5 minute too long for social media. 
- Version 3 - Create a hook to delete cache entry whenever db is updated. Force cache to update.
- Version 4 - A popular profile has a cache entry that is called on 1000s of times per second. When cache key expires, DB will be flooded with thousands of queries and may slow or go down. This scenario is known as the **cache stampede** or the **thundering herd**. Solution ensure the first query hits the database when multiple cache misses are reported within the same time, subsequent requests wait. Second add random seconds to each TTL to make sure different keys expire at different times. 

### Case Study 2: Scaling Gross Profit Report

The finance team runs a Gross Profit by Product Division report, pulled constantly throughout the day across Polaris, Beatrice, and Glenara Estates.

- Version 1 - One GL Entries table, no indexes. The report runs a full table scan, paying a disk seek per row. Fine at a few thousand rows.
  - Drawback - As GL Entries grows into the millions, the report gets slower every month, and it competes for the same table that POS sync is actively writing dispatch entries into during the morning sync window.
- Version 2 - Add an index on the columns the report actually filters and groups by (company_id, account). Lookups go from a table scan to a direct hit.
  - Drawback - Indexing speeds up the read, but every POS sync write now also has to update the index, and reads and writes are still fighting for the same instance's resources during the sync window - the report is fast again, but only when it's not sync time.
- Version 3 - Introduce a read replica. Reports read from the replica; POS sync writes still go to the master.
  - Drawback - The replica lags behind the master by some small window, so the report is now a few seconds or minutes stale. Acceptable for a Gross Profit report nobody needs to the millisecond - not acceptable if finance ever needs a same-second consolidated view across all three companies during a live sync.
- Version 4 - Even with a replica, one company's GL Entries table eventually outgrows what a single instance can serve well. Shard GL Entries by company_id, so Polaris, Beatrice, and Glenara Estates each live on their own shard.
  - Drawback - A single-company report is now fast (it only touches one shard), but a consolidated group-wide report has to query all three shards and merge in application code. Onboarding a fourth company later means most existing companies' shard assignments could shift - this is exactly where consistent hashing earns its keep.
- Version 5 - The Gross Profit report specifically is still the single most expensive read in the system, even sharded. Denormalize it: maintain a flattened, pre-joined read table (or a materialized view) refreshed on a schedule, so the report never runs the join/aggregate at read time at all.
  - Drawback - The flattened table is now a fourth copy of derived data to keep in sync. Acceptable because this report is read constantly and updated rarely - the same "read-heavy, write-light" justification that made write-through the right caching choice for the voided-order case earlier.

Notice the shape: each version fixes the previous drawback and introduces a new, smaller one - and every fix maps directly onto a technique in the Decision Matrix below (indexing, replication, sharding, denormalization, in that order).








### Estimation Foundation
A good estimate that is closest to reality is instrumental to addressing a problem. For example, when considering scaling, whether to use Cache, Horizontal or Vertical Scaling or when selecting a database optimization strategy, a good estimate of your needs will guide your decision. There are a few heuristics and tools we can use to come up with helpful estimates.

### Back Of The Envelope Estimates
Draft mathematical estimates, the kind one would jot on a piece of paper. On the question of cache, try to estimate response times based on performance of typical operations. 

-   L1 cache reference 0.5 ns
-   Branch mispredict 5 ns - when a computer processor incorrectly guesses the path code will take at a conditional jump. This metric represents the waste  not have been executed had the branch been correctly predicted
-   L2 cache reference 7 ns - cache that sits between the tiny L1 cache and the larger L3 cache or main RAM, holding data the CPU is likely to use next to speed up tasks.
-   Mutex lock/unlock 25 ns - time taken to lock and unlock shared resources between threads
-   Main memory reference 100 ns - what an in-process Python object lookup costs; it's the baseline everything else gets compared against
-   Compress 1KB with Zippy 10,000 ns
-   Send 1KB over 1 Gbps network 10,000 ns
- Read 4 KB randomly from SSD 150,000 ns - the realistic "disk read" cost on modern infra, including our own DigitalOcean droplets
-   Read 1 MB sequentially from memory 250,000 ns
-   Round trip within same data-center 500,000 ns - your app server talking to a DB or Redis on the same DigitalOcean droplet.
- Read 1 MB sequentially from SSD 1,000,000 ns
-   Disk seek (HDD) 10,000,000 ns - the number everyone quotes for "a slow query," but it describes spinning disks, not the SSD-backed infra we actually run on.
-   Read 1 MB sequentially from network 10,000,000 ns - pulling a large report result set (Gross Profit by Division, COGS query) off disk lives in this range
-   Read 1 MB sequentially from disk 30,000,000 ns
-   Send packet CA->Netherlands->CA 150,000,000 ns - request from a field agent on a slow rural connection

The specifics of the nano second figures are not as important as the ratios between them. For instance the Main memory (100ns) to disk seek (10,000,000ns) is a 100,000x difference. Disk seek to a cross-continent network call (150,000,000ns) is another 15x on top of that and so forth. This is supposed to guide you on where it makes sense to prioritize your efforts for optimization. This is where an intuitive sense of the relationship between these metrics become invaluable.
 
### Power Of Two Table
Computers count in base 2 so an intuitive sense of the two table can be a useful tool in doing quick math to estimate data storage or all quantities that map to memory. 
| Power | Exact Value         | Approx Value | Bytes |
|------:|--------------------:|-------------|------:|
| 7     | 128                 |             | 128 B |
| 8     | 256                 |             | 256 B |
| 10    | 1,024               | 1 thousand  | 1 KB  |
| 16    | 65,536              |             | 64 KB |
| 20    | 1,048,576           | 1 million   | 1 MB  |
| 30    | 1,073,741,824       | 1 billion   | 1 GB  |
| 32    | 4,294,967,296       |             | 4 GB  |
| 40    | 1,099,511,627,776   | 1 trillion  | 1 TB  |
In line with the previous section, the power of tools table is a mental cheat sheet for BOTE estimations for storage. In a "how much disk space will a year of POS sync data need". <Need a simpler example to explain in the code and in the text>
## Caching Strategies
#### Cache Aside
- "Three checks on a miss". Describes the number of trips that are triggered when call is made to retrieve and un-cached value. We first check cache if the data we are looking for exists, if not in cache we retrieve from the database and stores a copy of the record for future reference. 
#### Write Through
- Writing to cache and the database at the same time. Better to have DB being the main source of truth.  This can lead to slower writes and memory wastage. *Write DB =>* Then Cache. Most suitable in scenarios of low write activities. 
#### Write Behind
- Speaks to the question "Are my transactions high volume?". If yes, for quicker writes, use the *Write Behind Pattern*. Write to cache first, deferred update to the database. Examples of where such a pattern would fit are "Last Seen Timestamps, Biometric or sensor readings in sum circumstances". Carries data loss risk using cache as primary data source.
#### Refresh Ahead
- Proactively update cached data in the background before its TTL expiration. Predictable, scheduled access: the Gross Profit or COGS reports that get pulled every morning, price lists checked constantly through the business day, or FOEP account-mapping config used on every dispatch call — refreshing it just before expiry means a dispatch never stalls on a slow re-fetch during a busy processing window

## DB Scaling Demo
### Sharding
A scaling technique (horizontal) involving splitting a larger database into smaller, independent portions (shards).


| Sharding Technique | Basic Description |
|--------------------|-------------------|
| **Range-based Sharding** | Based on a range of values, such as customer IDs or dates. |
| **Hash-based Sharding** | Using hash function on a key (e.g., Customer ID) to determine which shard stores the data.
| **Directory (Lookup)-based Sharding** | Uses a lookup table that maps each record or key to the shard where it is stored. |
| **Geo-based Sharding** | Partitions data by geographic region so users are served by a nearby database. |

### Replication Master - Slave Architecture
Scaling by serving copies of a database in different locations. The Master Slave pattern is best suited to financial data, having one source of truth lessens uncertainty and ambiguity. Writes go to a single **MASTER** instance or a select group of instances with write privileges and get copied to a number of replica (slave) instances, from which data is only read. Leaderless setups allow any instance to have read write privileges. They allow the ability to distribute write privileges regionally (Think AWS), however updates can be slow and error prone. Thus not the most appropriate for recording financial transactions.
### De-normalization (Controlled Redundancy)
Redundancy introduced on purpose, for the purpose of read efficiency. We reduce the number of Joins. Process where you optimize read performance by adding redundant data to multiple tables.  but comes at the expense of write performance.

### SQL or NoSQL
Before reaching for any of the scaling techniques above, the more basic question is whether a relational database is even the right tool for this data in the first place.

**Reasons to reach for SQL:** structured, well-defined schema; genuinely relational data where joins matter; you need transactions (ACID guarantees); access patterns benefit from fast indexed lookups.

**Reasons to reach for NoSQL:** semi-structured or frequently-changing schema; no real need for complex joins; very high write throughput or very large data volumes; the data is naturally key-value shaped.

For ERPs like ERPNext specifically: GL Entries, Delivery Notes, and anything tied to accounting is squarely SQL territory — the joins and transactional guarantees matter too much to give up. Something like POS terminal heartbeat/status pings or session tokens is a reasonable candidate to keep in Redis rather than ever writing to MariaDB at all — not "NoSQL instead of SQL" so much as "don't make this a database problem in the first place."

#### Indexing (SQL Tuning)
This is the direct follow-through on the disk-seek point earlier: an index turns "scan every row" into "look up directly" — the difference between a query costing a seek per row and costing a small, fixed number of seeks total. Columns you filter, sort, or join on (`WHERE`, `GROUP BY`, `ORDER BY`, `JOIN`) are the ones worth indexing.

The cost isn't free — every index makes writes slightly slower (the index has to be updated too) and takes up additional storage/memory. It's the same "read speed vs. write cost" trade-off as denormalization, just implemented differently: an index gives you the read speedup without duplicating the actual data.

#### Decision Matrix

| Technique | Solves | Cost | When to Reach for It | Example |
|-----------|--------|------|----------------------|-----------------|
| **Replication (master-slave)** | Read scaling & read availability | Replication lag; writes still bottlenecked on one instance | Read traffic ≫ write traffic, and some staleness on reads is acceptable | Dedicated read replica for ERP's reporting queries |
| **Sharding** | Write and read scaling by splitting the dataset | Cross-shard aggregates require application-level merging; resharding later is complex | A single instance can no longer hold or serve the full dataset or write load—validate this against your capacity estimates first | Splitting `GL Entry` records by `company_id` once row counts justify it |
| **De-normalization** | Read performance for specific, high-frequency queries | Additional write overhead, extra storage, and risk of inconsistent updates | One or two read paths dominate and are well understood in advance | Flattened farm/crop names for the Gross Profit report |


## Security

- **Encrypt in transit and at rest.** Data moving over the network (HTTPS/TLS) and data sitting on disk (encrypted volumes/columns) should both be protected.
- **Sanitize all user input**, including anything exposed to the user even indirectly, to prevent injection attacks — SQL injection, XSS — never trust that user-supplied text is safe to render or execute as-is.
- **Use parameterized queries** to prevent SQL injection specifically:
  - `login_vulnerable(username, password)` — builds the SQL query by directly splicing raw user input into an f-string. A crafted username like `' OR '1'='1' --` rewrites the WHERE clause into an always-true condition and returns a row with no valid credentials at all.
  - `login_safe(username, password)` — the identical query, but built with `?` placeholders instead of string interpolation. User input is always bound as a literal value to compare against, never treated as SQL syntax — so the exact same payload just fails to match anything, harmlessly.
- **Use the principle of least privilege.** A service account, API key, or role should only be able to do what it strictly needs to.
## Other Topics
-   CAP Theorem / Consistency Patterns
	- Principle  that states that a distributed system can only guarantee two out of 3 properties. Consistency, Availability or Partition tolerance.
-   Availability Math
	- The probability or percentage that a system is operational and accessible when needed.
-   REST vs. RPC
-   Message Queues / Async Processing (Frappe's RQ + Redis background jobs)
-   Load Balancing / Horizontal vs. Vertical Scaling

## Additional Reading
https://www.geeksforgeeks.org/system-design/cache-aside-pattern/
https://www.youtube.com/watch?v=f1pGzq551Kc&t=31s
https://dzone.com/articles/learn-database-read-write-splitting-using-your-bro
https://docs.oracle.com/cd/E13924_01/coh.340/e13819/readthrough.htm
https://github.com/donnemartin/system-design-primer#system-design-topics-start-here
https://highscalability.com/google-pro-tip-use-back-of-the-envelope-calculations-to-choo/
