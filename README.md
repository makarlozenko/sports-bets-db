# Sports Bets DB

MongoDB Atlas database + Flask REST API for a simple sports betting system.

Four core collections: `User`, `Team`, `Matches`, `Bets`.

Ready-to-use endpoints (Postman-friendly) and small automation scripts for end-to-end checks.

## Collections

* **User**

  * `email` (unique),
  * `firstName`,
  * `lastName`,
  * `balance`,
  * `nickname`,
  * `birthDate`,
  * `IBAN`,
  * `phone`

* **Team**

  * `coaches` : `{firstName, lastName, experienceYears, coachType}`,
  * `players` : `[{firstName, lastName, role, birthDate, achievements : {careerGoalsOrPoints, penaltiesReceived} }]`,
  * `rating`,
  * `sport` : `football | krepsinis`,
  * `teamName`

* **Matches**

  * `comand1` : `{name, result : []}`,
  * `comand2` : `{name, result : []}`,
  * `date` (`YYYY-MM-DD`),
  * `matchType`,
  * `sport`
  * `odd`

* **Bets**

  * `userEmail` (references `users.email`)
  * `userId`
  * `event`: `{team_1, team_2, type, date}`
  * `bet`: `{stake, odds, choise, team, createdAt}`
  * `status`: `pending | won | lost`

---
The schema of DB: 
Collections appear in blue, blank tables provide explanations for array fields.

<img width="2376" height="3463" alt="Untitled diagram-2025-10-11-183748" src="https://github.com/user-attachments/assets/3b48ace4-0007-449c-84af-a7ef5879e6ef" />

## Quick Start
**Config**

```python
from pymongo import MongoClient
client = MongoClient("mongodb+srv://arinatichonovskaja_db_user:<password>@sportbet.wafmb2f.mongodb.net/?retryWrites=true&w=majority&appName=SportBet")
db = client.SportBET
```

## Getting Started — run everything via `main.py`
---
## Test the API using Postman
curl http://127.0.0.1:5000/users

---
## Run scenarios for testing:
### **Scenario E2E (`scenario_e2e.py`)**
This script performs an end-to-end test of the betting API.
It:
1. Fetches the selected user’s current `/bets/summary`.
2. Creates a new `/matches` entry.
3. Posts a `/bets` record for that match and user.
4. Retrieves the summary again to compare results.
5. Deletes the created bet to clean up.

All requests are sent to the configured `BASE_URL` (default: `http://127.0.0.1:5050`).
### **How to run**
1. Make sure the betting API is running locally (default port **5050**).
2. Run the scenario script:
   ```bash
   python scenario_e2e.py
   ```
3. Check the console output for request details.

---
### **Scenario bets (`scenario_bets.py`)**
This script tests the betting-related API endpoints.
It:
1. Retrieves a user’s existing `/bets/summary`.
2. Creates one or more `/bets` for a selected user and match.
3. Verifies that the bet creation was successful.
4. Fetches the updated `/bets/summary` to confirm the change.

The test ensures that the `/bets` creation and summary calculation logic work correctly.
All requests are sent to the configured `BASE_URL` (default: `http://127.0.0.1:5050`).

### **How to run**
1. Make sure the betting API is running locally (default port **5050**).
2. Run the scenario script:
   ```bash
   python scenario_bets.py
   ```
3. Review the console output for request responses and summaries.

### All endpoints (more details can be found in the other README files for each collection):
## Checking health of DB
### `GET /health`

**Purpose:** Basic system health check.
**Returns:**

`{ "ok": true,
   "db": "SportBET", 
   "collections": [...] }`

---

## Users
### `GET /users`
**Description:** Returns all users, optionally filtered and sorted.
**Query Parameters:**

* `firstName` 
* `lastName` 
* `min_balance`, `max_balance` 
* `sort_by` = `balance|firstName|lastName`
* `ascending` = `true|false`

### `GET /users/<id>`
Get a single user by Mongo `_id`.

### `GET /users/by_email/<email>`
Find a user by email (case-insensitive).

### `POST /users`
**Creates a new user.**
**Body:**

```json
{
  "email": "user@example.com",
  "nickname": "nickname",
  "firstName": "John",
  "lastName": "Doe",
  "phone": "+37060000000",
  "IBAN": "LT601010012345678901",
  "birthDate": "1990-01-01",
  "balance": 10.50
}
```

**Notes:**
* Validates formats (email, phone, IBAN).
* Prevents duplicates by `email`, `nickname`, `phone`, or `IBAN`.
* `balance` stored as **Decimal128**.

### `PATCH /users/<id>`
**Partially updates user info.**
Allowed fields:
`firstName`, `lastName`, `nickname`, `phone`, `IBAN`, `balance`, `birthDate`

* `balance` converted to `Decimal128`.
* `birthDate` parsed from `YYYY-MM-DD`.

### `DELETE /users/<id>`
Deletes a user by `_id`.

### `POST /users/update_balance`
**Sets the user's balance (absolute value).**

```json
{ "userId": "<mongo_id>",
  "balance": 42.75 }
```
* Replaces current balance with a new Decimal128 value.
* Returns updated balance as string for precision.

---
## Teams
### `GET /teams`
Lists all teams.
Returns: `{ "items": [...], 
            "total": <count> }`

### `POST /teams`
Creates a team.
Duplicate prevention by `teamName + sport` (case-insensitive).

### `GET /teams/<id>`
Returns team details by `_id`.

### `PATCH /teams/<id>`
Partial update of a team.

### `DELETE /teams/<id>`
Removes a team.

### `GET /teams/filter`
**Filters teams by fields.**
**Query:**
* `sport`
* `name` – regex on `teamName`
* `min_rating`, `max_rating`
  Returns `{ "items": [...],
              "total": <count>}`.

### `GET /teams/reorder`
Sorts all teams.
**Query:**
* `sort_by` (e.g. `rating`)
* `ascending=true|false`

---
### Aggregations
#### `GET /teams/aggregations/football_stats`
**Football stats summary (sport = "football"):**
Total goals scored/conceded, yellow/red cards for football teams.

#### `GET /teams/aggregations/basketball_stats`
**Basketball stats summary (sport = "krepsinis"):**
Calculates scored/conceded, goal_diff, avg_foul, match_count.

## Matches
### `GET /matches`
Returns all matches (filterable).
**Query:**
* `sport`
* `from`, `to` — date range

### `GET /matches/<id>`
Get one match by `_id`.

### `POST /matches`
Create a new match.
```http
POST /matches

{
  "matchType": "league",
  "sport": "football",
  "date": "2025-09-10",
  "comand1": {
    "name": "team1",
    "result": {
      "status": "won",
      "goalsFor": 2,
      "goalsAgainst": 1,
      "cards": {"red": 0, "yellow": 2}
    }
  },
  "comand2": {
    "name": "team2",
    "result": {
      "status": "lost",
      "goalsFor": 1,
      "goalsAgainst": 2,
      "cards": {"red": 0, "yellow": 1}
    }
  }
}
```
Prevents duplicates based on:
`sport + matchType + date + comand1.name + comand2.name`.

### `PATCH /matches/<id>`
Update match fields.

### `DELETE /matches/<id>`
Delete match by `_id`.

### `GET /matches/filter`
**Filter by:**
* `sport`
* `team` (regex match in `comand1.name` or `comand2.name`)
* `from` / `to` (date range)
  
### `GET /matches/reorder`
Sort matches.
**Query:**
* `sort_by=date|sport|matchType`
* `ascending=true|false`

---
## Bets
### `GET /bets`
List all bets with full filtering and sorting.

**Query:**
* `status=pending|won|lost`
* `team` — regex match (`event.team_1` or `event.team_2`)
* `event_start_date`, `event_end_date`
* `created_start_date`, `created_end_date`
* `sort_by` = `stake|odds|event_date|createdAt|bet_createdAt`
* `ascending=true|false`
* `limit`, `skip`

**Returns:**
```json
{
  "items": [...],
  "total": <int>,
  "query": { ... },
  "sorted_by": "event.date",
  "ascending": true,
  "limit": 100,
  "skip": 0
}
```

### `GET /bets/by_email/<email>`
Returns bets for a specific user.
Supports same filters as `/bets`.

### `POST /bets`
**Creates a new bet.**

```json
{
  "userEmail": "user@example.com",
  "userId": "6524a1f...",
  "event": {
    "team_1": "Team A",
    "team_2": "Team B",
    "type": "league",
    "date": "2025-09-01"
  },
  "bet": {
    "choice": "winner",
    "team": "Team A",
    "stake": 10.00,
    "odds": 2.5
  }
}
```

### `POST /bets/update_status`
Updates bet’s `status` (`pending → won|lost`).
**Body:**

```json
{ "betId": "<mongo_id>",
  "status": "won" }
```

### `DELETE /bets/<id>`
Deletes a bet from MongoDB.

---
## Agregation
### `GET /bets/summary`
Per-user aggregation with totals.
**Returns:**

```json
[
  {
    "userEmail": "user@example.com",
    "total_won": 200.0,
    "total_lost": 50.0,
    "final_balance": 150.0
  }
]
```
