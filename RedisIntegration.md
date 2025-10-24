# Sports Bets DB — Redis Integration

---

## Redis Connection & Caching Functions

### Redis Connection

```python
redis = Redis(host="localhost", port=6379, decode_responses=True)
```

This line establishes a connection to a local Redis instance.  
- **`host`**: Redis server location (`localhost` means it’s running on the same machine).  
- **`port`**: Default Redis port (`6379`).  
- **`decode_responses=True`** ensures data returned from Redis is automatically decoded into readable strings instead of bytes.

---

### Caching Functions Overview

These helper functions provide a simple caching layer for data that can be expensive to compute or query — such as **filtering, aggregation, or sorting** operations.

#### 1. `cache_get_json(key: str)`
Fetches a JSON-serialized value from Redis and deserializes it back to Python.
```python
def cache_get_json(key: str):
    data = redis.get(key)
    return json.loads(data) if data else None
```
- Retrieves data by `key`.
- Returns a Python object if the data exists, otherwise `None`.

#### 2. `cache_set_json(key: str, value, ttl: int)`
Stores data in Redis as JSON with a **time-to-live (TTL)**.
```python
def cache_set_json(key: str, value, ttl: int):
    jitter = random.randint(0, 10)
    redis.setex(key, timedelta(seconds=ttl + jitter), json.dumps(value))
```
- Serializes a Python object into JSON before storing it.
- TTL ensures cached results expire automatically.
- A small **random jitter** prevents simultaneous expirations (useful under heavy load).

#### 3. `invalidate(*keys)`
Manually deletes one or more cache entries.
```python
def invalidate(*keys):
    if keys:
        redis.delete(*keys)
```
Used when underlying data changes — for example, when new bets are added or a match result changes.

#### 4. `invalidate_pattern(pattern: str)`
Deletes all keys matching a given pattern.
```python
def invalidate_pattern(pattern: str):
    for key in redis.scan_iter(pattern):
        redis.delete(key)
```
Useful when we want to clear a group of related cached values (e.g., all bets for a certain user).

---

## TTL and Invalidation Mechanics

**TTL (Time-To-Live)** defines how long a cached entry stays in Redis before expiring automatically.  
When a TTL is set:
- Redis automatically deletes the key once the time has passed.
- This keeps cached data fresh and memory usage low.
- The **jitter** (a small random offset) ensures multiple cached items don’t expire simultaneously — reducing the risk of performance spikes.

**Invalidation** mechanisms (`invalidate` and `invalidate_pattern`) allow manual control over cache freshness:
- They are used when the source data changes.
- Example: after updating a bet, you’d call  
  ```python
  invalidate_pattern("bets:list:*")
  invalidate_pattern(f"bets_by_email:{user_email}:*")
  invalidate("bets_summary")
  ```  
  to ensure subsequent queries pull updated data instead of stale cache.

---

## Betting Logic & Concurrency Protection

This module handles **bet creation** and ensures **data consistency** when multiple users (or threads) attempt to place bets simultaneously.  
It prevents duplicate bets, protects user balances, and uses **Redis locks** to avoid race conditions.

### Key Features
- **Flask-based API** for managing users, matches, and bets.  
- **Duplicate bet protection** — users cannot place identical bets twice.  
- **Redis lock system** — prevents concurrent balance updates.  
- **Thread-safety testing** with `test_locks.py`.  
- **Automatic validation** of matches and bet types.

### How It Works
1. When a user places a bet:
   - The system checks if the match exists.  
   - It verifies that the user hasn’t already placed the same bet.  
   - It acquires a **Redis lock** to prevent simultaneous modifications.
2. If all checks pass, the bet is saved to the database.
3. If a duplicate or race condition is detected, the second operation is rejected safely.

**Example lock key:**
```python
lock_key = f"bet:{userId}:{event['team_1']}:{event['team_2']}:{event['date']}"
```

This ensures unique locks per user and match combination.

---

## Betting Cart System

This part implements a **Redis-based betting cart** that allows users to temporarily store bets before confirming them.  
It acts as a **fast, isolated layer** between users and MongoDB.

### How It Works
- Each user has a Redis hash where every bet item is stored as JSON.
- The system refreshes the cart’s **TTL** on every operation, keeping it alive for **3 days** of inactivity.
- Users can:
  - Add, update, or remove bets.
  - View the cart’s contents.
  - Clear the entire cart.
  - Perform **checkout**, which:
    - Validates the user in MongoDB.
    - Checks available balance.
    - Deducts the total stake.
    - Moves bets from Redis → MongoDB.
    - Clears the cart afterward.

If any error occurs during checkout, the operation **rolls back** — restoring balance and removing partial data.

### Benefits
- **Speed:** Redis handles all temporary betting data.  
- **Reliability:** MongoDB stores finalized bets.  
- **Data Integrity:** Checkout guarantees atomicity even under concurrent load.  
- **TTL-based cleanup:** Automatically removes stale carts.  

### Test Example
`test_cart_flow.py` demonstrates the workflow:
1. Add two bets to a cart.
2. Verify Redis contains the bets.
3. Ensure MongoDB is empty before checkout.
4. Perform checkout and verify bets appear in MongoDB.
5. Confirm the cart is cleared.

---

## Summary

Redis powers **three key components** in this system:
1. **Caching Layer** — speeds up heavy read operations.  
2. **Locking System** — prevents race conditions during bet placement.  
3. **Cart Storage** — holds temporary bets with TTL-based lifecycle management.

Together, they ensure **high performance**, **data integrity**, and **smooth concurrency handling** for the Sports Bets DB project.
