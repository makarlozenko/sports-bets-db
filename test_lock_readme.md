# Sports Bets DB — Betting Logic & Concurrency Protection

This module handles bet creation and ensures data consistency when multiple users (or threads) try to place bets at the same time.  
It prevents duplicate bets, protects user balance operations, and uses **Redis locks** to avoid race conditions.

---

## Features

- **Flask-based API** for managing users, matches, and bets  
- **Duplicate bet protection** — one user cannot place the same bet twice on the same match  
- **Redis lock system** — prevents concurrent balance updates or bet duplication  
- **Thread-safety test** via `test_locks.py`  
- **Automatic validation** of existing matches and bet types  

---

## How It Works

1. When a user places a bet (`POST /bets`), the system:
   - checks if the specified match exists;
   - verifies that the same user hasn’t already placed an identical bet;
   - acquires a **Redis lock** to ensure no other request is modifying that user’s bets simultaneously.
2. If everything is valid, the bet is saved in the database.
3. If a duplicate or race condition occurs, the system safely rejects the second request.

Example lock key:
```python
lock_key = f"bet:{userId}:{event['team_1']}:{event['team_2']}:{event['date']}"