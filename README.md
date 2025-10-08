# Sports Bets DB 
MongoDB Atlas database + Flask REST API for a simple sports betting system. Four core collections: `User`, `Team`, `Matches`, `Bets`. 
Ready-to-use endpoints (Postman-friendly) and small automation scripts for end-to-end checks.

## Collections

* **User**
  
  * `email` (unique), `firstName`, `lastName`, `balance`, `nickname`, `birthDate`, `IBAN`, `phone`
    
* **Team**

  * `coaches`, `players`, `rating`, `sport`, `teamName`
* **Matches**

  * `team_1`, `team_2`, `date` (`YYYY-MM-DD`), `matchType`, `sport`
* **Bets**

  * `userEmail` (references `users.email`)
  * `event`: `{ team_1, team_2, date }`
  * `bet`: `{ stake, odds }`
  * `status`: `pending | won | lost`
  *  Rule: one bet per user per event (enforced in code/logic)

## API (main endpoints)

```
GET    /bets
POST   /bets
GET    /bets/summary           # per-user won/lost/final balance summary
DELETE /bets/<bet_id>

GET    /matches
POST   /matches

GET    /teams
POST   /teams

GET    /users
POST   /users
```

### Examples

**Create a user**

```http
POST /users
Content-Type: application/json

{
  "firstName": "Rokas",
  "lastName": "Sabonis",
  "email": "rokisab@example.com",
  "balance": 10
}
```

**Create a match**

```http
POST /matches

{
  "matchType": "league",
  "sport": "football",
  "kada": MATCH_DATE,
  "komanda1": {
    "pavadinimas": TEAM_1,
    "result": {
      "status": "won",
      "goalsFor": 2,
      "goalsAgainst": 1,
      "cards": {"red": 0, "yellow": 2}
    }
  },
  "komanda2": {
    "pavadinimas": TEAM_2,
    "rezultatai": {
      "status": "lost",
      "goalsFor": 1,
      "goalsAgainst": 2,
      "cards": {"red": 0, "yellow": 1}
    }
  }
}
```

**Create a bet**

```http
POST /bets
Content-Type: application/json

{
  "userEmail": "rokisab@example.com",
  "event": { "team_1": "Team A", "team_2": "Team B", "date": "2025-10-08" },
  "bet": { "stake": 10.0, "odds": 2.5 },
  "status": "pending"   // or "won"/"lost"
}
```

**Summary**

```http
GET /bets/summary
# -> [
#   { "userEmail": "arina@example.com", "total_won": 25.0, "total_lost": 10.0, "final_balance": 15.0 },
#   ...
# ]
```

**Delete a bet**

```http
DELETE /bets/<bet_id>
```

## Quick Start

1. **Config (MongoDB Atlas)**
   Create `.env`:

   ```
   MONGODB_URI="mongodb+srv://<user>:<pass>@<cluster>/<db>?retryWrites=true&w=majority"
   DB_NAME="sports_bets"
   ```
2. **Install**

   ```bash
   pip install -r requirements.txt
   ```
3. **Run**

   ```bash
   python main.py
   # or: flask --app main run --port 5050 --debug
   ```

   Default dev URL: `http://127.0.0.1:5050`.

## E2E Scenarios (optional)

* `scenario_e2e.py` — show summary (before) → create a match → create a new bet → show summary (after) + deltas → delete the bet.

> Before running, edit `BASE_URL` and `USER_EMAIL`.

## Notes

* The summary (`/bets/summary`) uses only **settled** bets: `won` and `lost`. `pending` is excluded.
* If Atlas IP access control is enabled, add your current IP in **Network Access**.
* If you enforce uniqueness, use a composite rule like one bet per `userEmail + event`.

