# Sports Bets DB 

MongoDB Atlas + Flask REST API for a simple sports betting system.
**All filtering/sorting is done by MongoDB (server-side), not Python.**

* **Collections:** `users`, `teams`, `matches`, `bets`
* **Base URL (dev):** `http://127.0.0.1:5050` *(adjust if you run on another port; some examples below show `:5000`—replace accordingly)*

---

## Bets

### List & Filter

`GET /bets` with query params (all filters are **server-side** via MongoDB):

* **By status**

  * `/bets?status=won`
  * `/bets?status=lost`
  * `/bets?status=pending`

* **By team name** (matches if team appears in the event)

  * `/bets?team=Vilnius%20FC`

* **By date intervals** (event date and/or bet creation date)

  * **Combined:**

    ```
    /bets?event_start_date=2025-10-01&event_end_date=2025-10-20&created_start_date=2025-09-01&created_end_date=2025-09-30
    ```
  * **Event date only:**

    ```
    /bets?event_start_date=2025-10-01&event_end_date=2025-10-20
    ```
  * **Created date only:**

    ```
    /bets?created_start_date=2025-09-01&created_end_date=2025-09-30
    ```

* **Sorting** (ascending = `true|false`)

  * By stake: `/bets?sort_by=stake&ascending=false`
  * By odds: `/bets?sort_by=odds&ascending=false`
  * By created date: `/bets?sort_by=createdAt&ascending=false`
  * By event date: `/bets?sort_by=event_date&ascending=false`

### Aggregations

* **Summary per user:**
  `GET /bets/summary`
  Returns an array like:

  ```json
  [
    { "userEmail": "user@example.com", "total_won": 25.0, "total_lost": 10.0, "final_balance": 15.0 }
  ]
  ```

### Create a Bet

`POST /bets`

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

**Delete a Bet**
`DELETE /bets/<bet_id>`
Example:

```
DELETE /bets/68e3f5adfef4d19e2273bcf2
```

---

## Users

### List & Filter

`GET /users` with query params (server-side via MongoDB):

* **By name / surname / balance interval**

  ```
  /users?firstName=Edvinas&lastName=Masiulis&min_balance=1000&max_balance=2000
  ```

* **Sorting by balance**

  ```
  /users?sort_by=balance&ascending=false
  ```

### Create a User

`POST /users`

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

**Delete a User**
`DELETE /users/<user_id>`
Example:

```
DELETE http://127.0.0.1:5050/users/68e3f5adfef4d19e2273bcf2
```

*(If your server runs on 5000, use `http://127.0.0.1:5000`.)*

---

## Matches & Teams (basic)

* `GET /matches`, `POST /matches`
* `GET /teams`, `POST /teams`

Example `POST /matches`:

```json
{
  "team_1": "Team A",
  "team_2": "Team B",
  "date": "2025-10-08"
}
```

---

## Notes

* All filters/sorts are implemented with **MongoDB queries/aggregations** for scalability.
* `bets/summary` counts **settled** bets (`won`/`lost`); `pending` is excluded from won/lost totals.
* Ensure MongoDB Atlas IP access and credentials are configured (see `.env`).
* Dev run:

  ```bash
  python main.py
  # or
  flask --app main run --port 5050 --debug
  ```

---

## Optional Scripts

* `scenario.py` — create a bet → show that user’s summary → delete the bet.
* `scenario_e2e.py` — show summary (before) → create a match → create a new bet → show summary (after) + deltas → delete the bet.

> Edit `BASE_URL` and user email in scripts before running.
