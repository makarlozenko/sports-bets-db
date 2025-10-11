
# Sports Bets API

A simple REST API for managing users and bets for sports matches.

**Base URL**

```
http://127.0.0.1:5050
```

## Users

### List users

```
GET /users
```

**Example**

```http
GET http://127.0.0.1:5050/users
```

### Filtering

Filter by first/last name (case-insensitive, partial) and balance range.

```http
GET http://127.0.0.1:5050/users?firstName=Edvinas&lastName=Masiulis&min_balance=1000&max_balance=2000
```

**Query params**

* `firstName` – partial match (case-insensitive)
* `lastName` – partial match (case-insensitive)
* `min_balance`, `max_balance` – numeric range (float)

### Sorting

```
GET /users?sort_by=<field>&ascending=<bool>
```

**Allowed values**

* `sort_by`: `balance | firstName | lastName`
* `ascending`: `true | false` (also accepts `1 | yes | y`)

**Example**

```http
GET http://127.0.0.1:5050/users?sort_by=balance&ascending=false
```

### Create a user

```
POST /users
Content-Type: application/json
```

**Body**

```json
{
  "firstName": "John",
  "lastName": "Doe",
  "phone": "+1234567890",
  "email": "john.doe@example.com",
  "birthDate": "1990-05-15",
  "IBAN": "EE001122334455667788",
  "balance": 500.75,
  "nickname": "johnny"
}
```

> Required fields: `email`, `nickname`, `firstName`, `lastName`, `phone`, `IBAN`.
> `balance` is optional; stored as Decimal internally.

### Delete a user

```
DELETE /users/<id>
```

**Example**

```http
DELETE http://127.0.0.1:5050/users/68e3f5adfef4d19e2273bcf2
```

---

## Bets

### List bets

```
GET /bets
```

**Example**

```http
GET http://127.0.0.1:5050/bets
```

### Filtering

**Query params**

* `status` — `pending | won | lost`
* `team` — exact team name (case-insensitive)
* `event_start_date`, `event_end_date` — event (match) date range, **YYYY-MM-DD**
* `created_start_date`, `created_end_date` — creation date range (checks both `createdAt` and `bet.createdAt`), **YYYY-MM-DD**
* `limit` — page size (default 100, max 1000)
* `skip` — offset for pagination

**Examples**

```http
# All pending, sort by stake desc, limit 50
GET http://127.0.0.1:5050/bets?status=pending&sort_by=stake&ascending=false&limit=50

# Filter by team (exact name, case-insensitive)
GET http://127.0.0.1:5050/bets?team=Vilnius%20FC

# Event date range (from–to)
GET http://127.0.0.1:5050/bets?event_start_date=2025-10-01&event_end_date=2025-10-31

# Created date range + pagination
GET http://127.0.0.1:5050/bets?created_start_date=2025-09-01&created_end_date=2025-09-30&limit=25&skip=25

# Combined filter
GET http://127.0.0.1:5050/bets?status=won&team=Kaunas%20United&event_start_date=2025-10-01&event_end_date=2025-10-31&sort_by=event_date&ascending=true
```

### Sorting

```
GET /bets?sort_by=<field>&ascending=<bool>
```

**Allowed values**

* `sort_by`: `stake | odds | event_date | createdAt | bet_createdAt`
* `ascending`: `true | false` (also accepts `1 | yes | y`)

**Examples**

```http
GET /bets?sort_by=stake&ascending=false
GET /bets?sort_by=odds&ascending=false
GET /bets?sort_by=createdAt&ascending=false
GET /bets?sort_by=event_date&ascending=false
```

### Aggregations

Overall summary by user email (totals won/lost and net balance):

```http
GET http://127.0.0.1:5050/bets/summary
```

### Create a bet

```
POST /bets
Content-Type: application/json
```

**Body (winner)**

```json
{
  "userId": "d86b5f978ef1d4c0d78134b4",
  "userEmail": "arci.masiulis0@outlook.com",
  "event": {
    "team_1": "Kaunas Green",
    "team_2": "Klaipeda Mariners",
    "type": "league",
    "date": "2025-10-13"
  },
  "bet": {
    "choice": "winner",
    "team": "Kaunas Green",
    "odds": 2.29,
    "stake": 50.51
  }
}
```

> Notes:
>
> * `choice` must be `winner` **or** `score`.
> * If `choice = "winner"` → `bet.team` is required (`"TeamName"` or `"draw"`).
> * If `choice = "score"` → `bet.score.team_1` and `bet.score.team_2` are required (non-negative integers).
> * The API validates that a matching **match** exists in the `Matches` collection for the **same day** and the **same teams**.

### Delete a bet

```
DELETE /bets/<id>
```

**Example**

```http
DELETE http://127.0.0.1:5050/bets/68e3f5adfef4d19e2273bcf2
```

---

## Date Notes

* `event.date` supports either a **`YYYY-MM-DD`** string or a Mongo **Date** (naive UTC).
* The `/bets` filter works for both formats.

---

## Common Status Codes

* `200 OK` — success
* `201 Created` — resource created
* `400 Bad Request` — invalid parameters/format (e.g., wrong date format)
* `404 Not Found` — not found
* `409 Conflict` — duplicate (when applicable)
* `500 Internal Server Error` — unexpected error




If you want, I can add a **Matches** section (CRUD + examples) too, so the README covers the full flow end-to-end.
