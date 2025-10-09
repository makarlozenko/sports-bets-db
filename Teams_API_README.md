# 🏟️ Teams API (Flask + MongoDB)

This API manages **sports teams** (football, basketball, etc.) stored in MongoDB.  
It supports full CRUD operations, filtering, sorting, and data aggregations.

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
  "collections": ["Team", "Matches", "Bets"]
}
```

---

## 🧩 CRUD Operations

### ➕ Create Team
**POST** `/teams`

**Body (JSON):**
```json
{
  "sport": "football",
  "teamName": "Kaunas FC",
  "rating": 1850,
  "coaches": [
    {"firstName": "Mantas", "lastName": "Barauskas", "experienceYears": 8, "coachType": "head coach"}
  ],
  "players": [
    {
      "firstName": "Jonas",
      "lastName": "Petraitis",
      "role": "forward",
      "achievements": {"careerGoalsOrPoints": 22, "penaltiesReceived": 3}
    }
  ]
}
```

**Response:**
```json
{
  "_id": "671e8a57f7b0d4ab327a88f4",
  "sport": "football",
  "teamName": "Kaunas FC",
  "rating": 1850
}
```

---

### 📋 Get All Teams
**GET** `/teams`

Returns all teams in the collection.

**Example:**
```
GET http://127.0.0.1:5000/teams
```

**Response:**
```json
{
  "items": [
    {"_id": "671e8a57f7b0d4ab327a88f4", "teamName": "Kaunas FC", "rating": 1850, "sport": "football"}
  ],
  "total": 1
}
```

---

### 🔍 Get Team by ID
**GET** `/teams/<id>`

Example:
```
GET /teams/671e8a57f7b0d4ab327a88f4
```

**Response:**
```json
{
  "_id": "671e8a57f7b0d4ab327a88f4",
  "teamName": "Kaunas FC",
  "sport": "football",
  "rating": 1850
}
```

---

### ✏️ Update Team
**PATCH** `/teams/<id>`

Example:
```
PATCH /teams/671e8a57f7b0d4ab327a88f4
```

**Body:**
```json
{
  "rating": 1900
}
```

---

### ❌ Delete Team
**DELETE** `/teams/<id>`

Example:
```
DELETE /teams/671e8a57f7b0d4ab327a88f4
```

**Response:**
```json
{"deleted": true, "_id": "671e8a57f7b0d4ab327a88f4"}
```

---

## 🔎 Filtering & Sorting

### 🔍 Filter Teams
**GET** `/teams/filter`

| Parameter | Type | Description |
|------------|------|--------------|
| `sport` | string | Filter by sport (e.g. football, basketball) |
| `name` | string | Filter by part of team name |
| `min_rating` | number | Minimum rating |
| `max_rating` | number | Maximum rating |

**Example:**
```
GET /teams/filter?sport=football&min_rating=1500&max_rating=2000
```

---

### 🔁 Reorder Teams
**GET** `/teams/reorder`

| Parameter | Type | Description |
|------------|------|--------------|
| `sort_by` | string | Field to sort by (`rating`, `teamName`) |
| `ascending` | bool | `true` for ascending, `false` for descending |

**Example:**
```
GET /teams/reorder?sort_by=rating&ascending=false
```

---

## 📊 Aggregations

### ⚽ Goals Summary
**GET** `/teams/aggregations/goals`

Calculates:
- Total scored goals/points per team  
- Estimated total conceded goals  
- Difference between them

| Parameter | Type | Description |
|------------|------|-------------|
| `sport` | string | Optional (`football` / `basketball`) |

**Example:**
```
GET /teams/aggregations/goals?sport=football
```

**Response:**
```json
[
  {
    "teamName": "Vilnius FC",
    "sport": "football",
    "total_scored": 187,
    "total_conceded": 131,
    "difference": 56
  }
]
```

---

### 🟨 Card Statistics
**GET** `/teams/aggregations/cards`

Calculates the **average yellow and red cards** per team  
(based on players’ `penaltiesReceived`).

| Parameter | Type | Description |
|------------|------|-------------|
| `sport` | string | Optional (`football` / `basketball`) |

**Example:**
```
GET /teams/aggregations/cards?sport=football
```

**Response:**
```json
[
  {
    "teamName": "Vilnius FC",
    "sport": "football",
    "avg_yellow_cards": 5.83,
    "avg_red_cards": 1.46
  }
]
```

---

## 🧠 Summary

| Category | Endpoint | Description |
|-----------|-----------|-------------|
| Health | `/health` | Check DB connection |
| CRUD | `/teams`, `/teams/<id>` | Basic operations |
| Filtering | `/teams/filter` | Filter by name, sport, or rating |
| Sorting | `/teams/reorder` | Reorder by rating or name |
| Aggregation | `/teams/aggregations/goals` | Total scored, conceded, difference |
| Aggregation | `/teams/aggregations/cards` | Average yellow/red cards |

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
http://127.0.0.1:5000/teams
```

---

**Author:** _Sports BET Project — University Exercise_  
**Module:** Teams (Part of “Team ir Matches”)
