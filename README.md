# Sports Bets DB 
MongoDB Atlas database + Flask REST API for a simple sports betting system. Four core collections: `User`, `Team`, `Matches`, `Bets`. 
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


## API (main endpoints)

```
GET    /bets
POST   /bets
GET    /bets/summary           # per-user won/lost final balance summary
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
  "firstName": "Edvinas",
  "lastName": "Masiulis",
  "phone": "+37064271769",
  "email": "edvinas.masiulis0@outlook.com",
  "birthDate": "1987-04-07",
  "IBAN": "EE685147538638153748",
  "balance": 12.00,
  "nickname": "edvinas0"
}
```

**Create a match**

```http
POST /matches

{
  "matchType": "league",
  "sport": "football",
  "date": 2025-09-10,
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

**Config**
 ```
 client = MongoClient("mongodb+srv://<user>:<pass>@<cluster>/<db>?retryWrites=true&w=majority")
 db = client.SportBET
 ```

