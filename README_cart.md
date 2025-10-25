# 🏆 SportBet — Betting Cart & Checkout System

This module implements a **temporary betting cart** using **Redis** and a **checkout system** that moves confirmed bets into **MongoDB**.  
It allows users to stage multiple bets before confirming them, while preventing duplicates and isolating each user’s data.

---

## ⚙️ Overview

### Architecture
- **Flask** — REST API framework  
- **Redis** — temporary cart storage (`TTL = 3 days`)  
- **MongoDB** — persistent storage for finalized bets  
- **UUID** — unique IDs for each cart item  
- **Decimal128** — accurate stake representation  

---

## 🧩 Cart Lifecycle

### 1️⃣ Add item to cart
**POST** `/cart/items`

```json
{
  "userEmail": "dovydas.sakalauskas5@gmail.com",
  "item": {
    "event": {
      "team_1": "Vilnius FC",
      "team_2": "Panevezys Town",
      "type": "league",
      "date": "2025-08-29"
    },
    "bet": {
      "choice": "winner",
      "team": "Panevezys Town",
      "stake": 25
    }
  }
}
```

✅ Response:
```json
{
  "message": "Added to cart",
  "itemId": "eb68eeca-40b8-46ee-aff2-0bad248254c2",
  "item": { ... }
}
```

Each user’s cart is stored under a unique Redis key:
```
app:cart:user:<userId_or_email>
```

---

### 2️⃣ View cart
**GET** `/cart?user=<userId_or_email>`

Example:
```
GET /cart?user=dovydas.sakalauskas5@gmail.com
```

Response:
```json
{
  "items": [
    {"id": "eb68eeca-...", "item": { ... }}
  ],
  "total": 2,
  "ttl": 259199
}
```

---

### 3️⃣ Update or delete cart items

- **PATCH** `/cart/items/<itemId>` → update an item  
- **DELETE** `/cart/items/<itemId>?user=<email>` → remove one  
- **DELETE** `/cart/clear?user=<email>` → clear entire cart  

Every action refreshes the TTL to keep the cart alive for 3 days.

---

### 4️⃣ Checkout (move from Redis → MongoDB)

**POST** `/cart/checkout`

```json
{
  "userEmail": "dovydas.sakalauskas5@gmail.com"
}
```

Performs these atomic steps:
1. Reads all user cart items from Redis  
2. Validates and sums stakes  
3. Checks user balance (must be ≥ total stake)  
4. Deducts total stake once  
5. Inserts bets into MongoDB  
6. Clears Redis cart  

✅ Example response:
```json
{
  "message": "Checkout successful",
  "count": 2,
  "betIds": ["68fb15416ef9ef7fcb2cffef", "68fb15416ef9ef7fcb2cfff0"]
}
```

---

## 🧠 Duplicate Protection

Before inserting each bet into MongoDB, the system checks for duplicates.  
If a user already has a bet on the **same teams, date, and bet type**, that entry is **skipped**.

✅ Example duplicate response:
```json
{
  "message": "Checkout successful (skipped 2 duplicate bets)",
  "count": 0,
  "skipped": 2,
  "betIds": []
}
```

This ensures users cannot accidentally re-place identical bets.

---

## 🔐 User Isolation

Each user has a separate Redis hash:
```
app:cart:user:<userId_or_email>
```

So multiple users can manage their carts simultaneously, with full data isolation.

---

## 🧾 Example MongoDB Schema

A bet document after checkout looks like this:

```json
{
  "_id": "67185a86e93d5ab6d17a73b0",
  "userEmail": "dovydas.sakalauskas5@gmail.com",
  "userId": "ee576a2c1f82513b2d4b8047",
  "event": {
    "team_1": "Vilnius FC",
    "team_2": "Panevezys Town",
    "type": "league",
    "date": "2025-08-29"
  },
  "bet": {
    "choice": "winner",
    "team": "Panevezys Town",
    "stake": 25.00
  },
  "status": "pending",
  "createdAt": "2025-10-23T20:17:34.120Z"
}
```

---

## 🧪 Test Script — `test_cart_flow.py`

A simple automated script is provided to test the full flow.

### 🔄 What it does
1. Removes any **test bets** for the current user (only matching teams/dates).  
2. Adds **two bets** into Redis.  
3. Shows Redis state.  
4. Verifies MongoDB is initially empty.  
5. Runs **checkout** — moves bets to MongoDB.  
6. Displays final states.  
7. Adds **identical bets again** and runs checkout — verifies they are **skipped**.

### ▶️ Run
```bash
python test_cart_flow.py
```

### 💡 Example output
```
=============== STEP 7 — perform checkout again (should skip duplicates) ===============
Checkout: 201
{'message': 'Checkout successful (skipped 2 duplicate bets)',
 'count': 0,
 'skipped': 2,
 'betIds': []}
```

---

## 📁 Project Structure

```
/SportBet
│
├── app.py
├── cart_routes.py          # This module (Redis cart + checkout logic)
├── bets_routes.py          # Regular bets endpoints
├── test_cart_flow.py       # End-to-end flow test
└── README.md
```

---

## 🧩 Summary

✅ **Redis** — fast temporary cart storage with TTL  
✅ **MongoDB** — permanent bets after checkout  
✅ **Duplicate-safe** checkout logic  
✅ **User-isolated** carts  
✅ **Full automation** test script  

---

**Author:** Dovydas Sakalauskas  
Part of the *SportBet* system — Betting Cart & Checkout Module 🏅
