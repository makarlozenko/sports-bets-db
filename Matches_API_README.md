# ⚽ Matches API (Flask + MongoDB)

This API manages **sports matches** (football, basketball, etc.) stored in MongoDB.  
It supports full CRUD operations and simple filtering & sorting.

---

## ⚙️ Base URL

```
http://127.0.0.1:5000
```

---

## 📚 Available Endpoints

### 🩵 Health Check
**GET** `/health`  
Returns database connection info.

**Response:**
```json
{
  "ok": true,
  "db": "SportBET",
  "collections": ["Matches", "Team", "Bets"]
}
```

---

## 🧩 CRUD Operations

### ➕ Create Match
**POST** `/matches`

**Body (JSON):**
```json
{
  "matchType": "league",
  "sport": "football",
  "kada": "2025-09-05",
  "komanda1": {
    "pavadinimas": "Vilnius FC",
    "result": {
      "status": "won",
      "goalsFor": 2,
      "goalsAgainst": 1,
      "cards": {"red": 0, "yellow": 2}
    }
  },
  "komanda2": {
    "pavadinimas": "Kaunas United",
    "rezultatai": {
      "status": "lost",
      "goalsFor": 1,
      "goalsAgainst": 2,
      "cards": {"red": 0, "yellow": 1}
    }
  }
}
```

**Response:**
```json
{
  "message": "Match added",
  "match": {
    "_id": "6720f12bf7b0d4ab327a88f4",
    "sport": "football",
    "matchType": "league",
    "kada": "2025-09-05"
  }
}
```

---

### 📋 Get All Matches
**GET** `/matches`

Returns all matches.

**Example:**
```
GET http://127.0.0.1:5000/matches
```

**Optional query parameters:**
- `sport` — filter by sport type
- `from` — starting date (inclusive)
- `to` — ending date (inclusive)

**Response:**
```json
{
  "items": [
    {"_id": "6720f12bf7b0d4ab327a88f4", "sport": "football", "matchType": "league"}
  ],
  "total": 1
}
```

---

### 🔍 Get Match by ID
**GET** `/matches/<id>`

Example:
```
GET /matches/6720f12bf7b0d4ab327a88f4
```

**Response:**
```json
{
  "_id": "6720f12bf7b0d4ab327a88f4",
  "sport": "football",
  "matchType": "league",
  "kada": "2025-09-05"
}
```

---

### ✏️ Update Match
**PATCH** `/matches/<id>`

Example:
```
PATCH /matches/6720f12bf7b0d4ab327a88f4
```

**Body:**
```json
{
  "matchType": "friendly"
}
```

**Response:**
```json
{
  "_id": "6720f12bf7b0d4ab327a88f4",
  "matchType": "friendly"
}
```

---

### ❌ Delete Match
**DELETE** `/matches/<id>`

Example:
```
DELETE /matches/6720f12bf7b0d4ab327a88f4
```

**Response:**
```json
{"deleted": true, "_id": "6720f12bf7b0d4ab327a88f4"}
```

---

## 🔎 Filtering & Sorting

### 🔍 Filter Matches
**GET** `/matches/filter`

| Parameter | Type | Description |
|------------|------|--------------|
| `sport` | string | Filter by sport (e.g. football, krepsinis) |
| `team` | string | Filter by team name (partially matches) |
| `from` | date | Start date (YYYY-MM-DD) |
| `to` | date | End date (YYYY-MM-DD) |

**Example:**
```
GET /matches/filter?sport=football&team=Vilnius&from=2025-09-01
```

**Response:**
```json
{
  "items": [
    {
      "sport": "football",
      "komanda1": {"pavadinimas": "Vilnius FC"},
      "komanda2": {"pavadinimas": "Kaunas United"}
    }
  ],
  "total": 1
}
```

---

### 🔁 Reorder Matches
**GET** `/matches/reorder`

| Parameter | Type | Description |
|------------|------|--------------|
| `sort_by` | string | Field to sort by (`kada`, `sport`) |
| `ascending` | bool | `true` for ascending, `false` for descending |

**Example:**
```
GET /matches/reorder?sort_by=kada&ascending=false
```

**Response:**
```json
[
  {"sport": "football", "kada": "2025-10-17"},
  {"sport": "football", "kada": "2025-09-29"}
]
```

---

## 🧠 Summary

| Category | Endpoint | Description |
|-----------|-----------|-------------|
| CRUD | `/matches`, `/matches/<id>` | Basic operations |
| Filtering | `/matches/filter` | Filter by sport, team name, or date range |
| Sorting | `/matches/reorder` | Sort matches by date or sport |

---

## 🧰 Tech Stack
- Python 3.10+
- Flask
- MongoDB (Atlas)
- PyMongo
- Postman (for testing)

---

## 🚀 Run Locally

```bash
python main.py
```

Then open:
```
http://127.0.0.1:5000/matches
```

---

**Author:** _Sports BET Project — University Exercise_  
**Module:** Matches (Part of “Team ir Matches”)
