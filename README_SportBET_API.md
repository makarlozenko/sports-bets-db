
# SportBET API — README

Išsamus REST API aprašas jūsų Flask + MongoDB projektui. Dokumente surinkti visi aptarti endpoint'ai, jų parametrai,
tipiniai atsakymai, klaidos ir svarbios pastabos apie **pinigų tikslumą (Decimal/Decimal128)**, **datų filtravimą**,
**agregacijas** ir **indeksus**.

> Ši versija atspindi jūsų dabartinį kodą (pagal pateiktus fragmentus) ir rekomenduojamus patobulinimus, kad
> **visa „aritmetika“ vyktų MongoDB pusėje**, o Python dalyje liktų tik validacija/serializacija.

---

## Turinys

- [Architektūra ir technologijos](#architektūra-ir-technologijos)
- [Bendros konvencijos](#bendros-konvencijos)
  - [Laikai ir datos](#laikai-ir-datos)
  - [Pinigai (Decimal/Decimal128)](#pinigai-decimaldecimal128)
  - [Paginacija ir rikiavimas](#paginacija-ir-rikiavimas)
  - [Bendri HTTP statusai](#bendri-http-statusai)
- [Health](#health)
- [Users](#users)
  - `GET /users`
  - `GET /users/<id>`
  - `GET /users/by_email/<email>`
  - `POST /users`
  - `PATCH /users/<id>`
  - `DELETE /users/<id>`
  - `POST /users/update_balance` *(absoliuti reikšmė)*
  - `POST /users/increment_balance` *(atominiam ± pokyčiui)*
- [Teams](#teams)
  - `GET /teams`
  - `POST /teams`
  - `GET /teams/<id>`
  - `PATCH /teams/<id>`
  - `DELETE /teams/<id>`
  - `GET /teams/filter`
  - `GET /teams/reorder`
  - Agregacijos: `GET /teams/aggregations/goals`, `GET /teams/aggregations/cards`, `GET /teams/aggregations/basketball_stats`
- [Matches](#matches)
  - CRUD: `GET /matches`, `GET /matches/<id>`, `POST /matches`, `PATCH /matches/<id>`, `DELETE /matches/<id>`
  - Filtras: `GET /matches/filter`
  - Rikiavimas: `GET /matches/reorder`
- [Bets](#bets)
  - `GET /bets`
  - `GET /bets/by_email/<email>`
  - `POST /bets`
  - `POST /bets/update_status`
  - `DELETE /bets/<id>`
  - Suvestinė: `GET /bets/summary` *(agregacija DB pusėje)*
- [MongoDB indeksai](#mongodb-indeksai)
- [Duomenų schemų pavyzdžiai](#duomenų-schemų-pavyzdžiai)
- [Pastabos apie apsaugą](#pastabos-apie-apsaugą)

---

## Architektūra ir technologijos

- **Flask** (REST API)
- **MongoDB** per **PyMongo**
- Atskiri moduliai „Users“, „Teams“, „Matches“, „Bets“.
- Visos sunkios užklausos (filtravimas, rikiavimas, `total`, agregacijos) vykdomos **MongoDB pusėje** (naudojant
  `find().sort().skip().limit()`, `count_documents()`, arba `aggregate` su `$facet`/`$group`).

## Bendros konvencijos

### Laikai ir datos
- Datoms naudokite **`datetime` (ISODate)** MongoDB'e, **ne string**. API priima `YYYY-MM-DD` ir (arba) ISO-8601.
- Filtravimas daromas DB pusėje, su `{"$gte": from, "$lte": to}`.
- Kai kur suderinamumo sumetimais dar palaikomas `event.date` kaip **String** (`YYYY-MM-DD`) — rekomendacija
  vienodinti į **Date**.

### Pinigai (Decimal/Decimal128)
- Jokio `float` pinigams → naudoti **`decimal.Decimal`** Pythone ir **`bson.decimal128.Decimal128`** MongoDB.
- Apvalinimas: **2 skaitmenys** su **`ROUND_HALF_UP`**.
- Atsakyme grąžinti sumas **string** (ne `float`), arba per `ser()` konvertuoti `Decimal128` į string.

### Paginacija ir rikiavimas
- Parametrai: `page`/`limit` (arba `skip`/`limit`), `sort_by`, `ascending`.
- Rikiavimas ir paginacija vykdomi DB pusėje (`sort/skip/limit`). `total` – per `count_documents()` arba `aggregate+$count`.

### Bendri HTTP statusai
- `200 OK` – sėkmė
- `201 Created` – sėkmingas sukūrimas
- `400 Bad Request` – validacijos klaida
- `404 Not Found` – įrašas nerastas
- `409 Conflict` – unikalumo pažeidimas / dublikatas
- `500` – nenumatyta klaida

---

## Health

### `GET /health`
Grąžina bazinę info apie servisą ir Mongo kolekcijas.

**Atsakymas**
```json
{
  "ok": true,
  "db": "SportBET",
  "collections": ["Users","Teams","Matches","Bets", "..."]
}
```

---

## Users

### `GET /users`
Filtras pagal `firstName`, `lastName`, balanso ribas (`min_balance`/`max_balance`). Rikiavimas pagal `balance|firstName|lastName`. Paginacija (`page`/`limit` arba `skip`/`limit`).

**Pvz.**
```
GET /users?firstName=Jon&min_balance=10&sort_by=balance&ascending=false&page=1&limit=20
```

**Atsakymas**
```json
{
  "items": [ { "id": "...", "firstName": "Jonas", "balance": "123.45", ... } ],
  "total": 42,
  "page": 1,
  "limit": 20
}
```

> `total` skaičiuojamas **DB pusėje** per `count_documents`.

### `GET /users/<id>`
Gauti vartotoją pagal `_id`.

### `GET /users/by_email/<email>`
Gauti vartotoją pagal el. paštą (rekomenduojama laikyti `email_lower` ir turėti indeksą).

### `POST /users`
Sukūrimas su normalizacija/validacija:
- Privalomi: `email`, `nickname`, `firstName`, `lastName`, `phone`, `IBAN`
- Pasirinktinai: `balance` (`Decimal128`), `birthDate` (`YYYY-MM-DD`)
- Dublikatai: **unikalūs indeksai** `email`, `nickname`, `phone`, `IBAN`. Gaudomas `DuplicateKeyError`.

### `PATCH /users/<id>`
Leidžiami laukai: `firstName`, `lastName`, `nickname`, `phone`, `IBAN`, `balance`, `birthDate`.
- `balance` – `Decimal128`
- `birthDate` – `datetime` (YYYY-MM-DD)
- Gaudomas `DuplicateKeyError` jei pažeidžiamas unikalumas.

### `DELETE /users/<id>`
Pašalina įrašą (`delete_one`).

### `POST /users/update_balance` *(absoliuti reikšmė)*
Nustato balansą į konkrečią sumą. Piniginė vertė validuojama `Decimal` ir saugoma kaip `Decimal128`. Atsakyme grąžinama **string**.

### `POST /users/increment_balance` *(rekomenduojama operacijoms)*
Atominis **± delta** balanso pakeitimas (`$inc`), tinka įnešimams/laimėjimams/nuostoliams.
Kūne: `{ "userId": "...", "delta": 12.50 }` (arba `-5.00`).

---

## Teams

### `GET /teams`
Sąrašas. Rekomenduojama pridėti paginaciją ir rikiavimą (`rating` pagal nutylėjimą). `total` per `count_documents` arba `$facet`.

### `POST /teams`
Sukuria komandą. Dublikato prevencija `teamName + sport`:
- Programiškai tikrinama **ir**/arba per **unikalų indeksą** su `collation` (case-insensitive).

### `GET /teams/<id>` / `PATCH /teams/<id>` / `DELETE /teams/<id>`
Standartinis CRUD.

### `GET /teams/filter`
Filtrai: `sport`, `name` (regex, case-insensitive), reitingo rėžiai `min_rating`/`max_rating`. `total` per `count_documents`.
Paginacija + rikiavimas rekomenduotini.

### `GET /teams/reorder`
Rikiavimas pagal `rating|teamName|created_at|updated_at|sport`, su whitelistu. Paginacija.

### Agregacijos
- `GET /teams/aggregations/goals` – **sumuoja** komandų žaidėjų `careerGoalsOrPoints` (Mongo `$sum`).
- `GET /teams/aggregations/cards` – **vidurkis** `penaltiesReceived` per žaidėją (Mongo `$avg`). 
- `GET /teams/aggregations/basketball_stats` – sudėtingesnė pipeline su `$lookup` į `Matches`, skaičiuoja:
  - `total_scored`, `total_conceded`, `goal_diff`, `avg_fouls`, `match_count`.

> Visos agregacijos vykdomos **MongoDB pusėje** su `aggregate`.

---

## Matches

### `GET /matches`
Filtrai: `sport`, datų intervalas (`from`/`to` — kaip `datetime`). `total` per `count_documents` arba `$facet`.
Rikiavimas + paginacija.

### `GET /matches/<id>`
Gauti vieną match’ą.

### `POST /matches`
Sukūrimas su dublikato prevencija: `(sport, matchType, date, comand1.name, comand2.name)`
– rekomenduojamas **unikalus indeksas** + `DuplicateKeyError`. `date` – **datetime** (ne string).

### `PATCH /matches/<id>` / `DELETE /matches/<id>`
Standartinis atnaujinimas ir trynimas. Pasirinktinai – optimistinė konkurencija per `updated_at`.

### `GET /matches/filter`
Filtrai: `sport`, `team` (regex, ieško `comand1.name` ir `comand2.name`), datų intervalas (`from`/`to` — `datetime`).
Paginacija + rikiavimas. `total` per `count_documents`.

### `GET /matches/reorder`
Rikiavimas: `date|sport|created_at|updated_at` (whitelist), su paginacija.

---

## Bets

### `GET /bets`
Filtrai: `status`, `team` (tiksli regex, case-insensitive), event datos intervalas (`event_start_date`/`event_end_date`),
sukūrimo datos intervalas (`created_start_date`/`created_end_date`).  
Rikiavimas: `stake|odds|event_date|createdAt|bet_createdAt`.  
Paginacija: `skip`/`limit`.  
`total` – **DB pusėje** (`count_documents`).

> Pastaba: kol palaikomas `event.date` dvigubas tipas (Date ir String), užklausa turi `$or` su abiem atšakom.
> Rekomenduojama migruoti į **vieną tipą (Date)**.

### `GET /bets/by_email/<email>`
Tos pačios filtravimo taisyklės (status/team/date range), bet ribota konkrečiam `userEmail`. `total` per `count_documents`.
Paginacija – rekomenduojama.

### `POST /bets`
Sukuria statymą:
- Privalomi: `userEmail`, `event.team_1`, `event.team_2`, `event.date`, `bet.choice`
- `bet.stake` → **Decimal128 (2 skaitmenys)**; `bet.odds` → `float` (arba Decimal, jei pageidaujate)
- `status` ∈ `{pending, won, lost}` (default `pending`)
- Match lookup pagal komandas + datą (pagal dieną, leidžiant komandų sukeitimą).
- Dublikato prevencija: tas pats vartotojas, ta pati diena (arba data string), tos pačios komandos (bet kuria tvarka) ir
  ta pati `bet.choice`. **Rekomendacija**: dėti **unikalų indeksą** atitinkamiems laukams ir gaudyti `DuplicateKeyError`.

### `POST /bets/update_status`
Keičia statymo `status`. Rekomendacijos:
- Validuoti status’ą (`pending|won|lost`).
- Jei pereinama iš `pending` į `won|lost`, atlikti **balanso settlement** vartotojui **atominiu `$inc`**:
  - `won`: kredituoti `payout = stake * odds` (arba tik profitą, jeigu tokia taisyklė)
  - `lost`: debetuoti `stake`
- Grąžinti atnaujintą `bet` ir naują vartotojo balansą.

### `DELETE /bets/<id>`
Pašalina statymą. Jei turite settlement žurnalą, apsvarstykite „compensation“/soft-delete.

### `GET /bets/summary`
**Agregacija DB pusėje** pagal `userEmail`:
- `total_won`: suma `stake*odds` kur `status=won`
- `total_lost`: suma `stake*odds` (arba tik `stake`, jei taip sutariate) kur `status=lost`
- `final_balance = total_won - total_lost`

> Ši suvestinė turėtų būti įgyvendinta su `aggregate` (`$match` + `$group` + `$project`), ne Pythone.

---

## MongoDB indeksai

Rekomenduojamas minimalus rinkinys (priderinkite prie realių užklausų):

```js
// Users
db.Users.createIndex({ email: 1 }, { unique: true })
db.Users.createIndex({ balance: 1 })

// Teams
db.Teams.createIndex({ sport: 1 })
db.Teams.createIndex({ rating: -1 })
db.Teams.createIndex({ teamName: 1 })
db.Teams.createIndex({ teamName: 1, sport: 1 }, { unique: true, collation: { locale: "en", strength: 2 } })

// Matches
db.Matches.createIndex({ "comand1.name": 1 })
db.Matches.createIndex({ "comand2.name": 1 })
db.Matches.createIndex({ date: -1 })
// Unikalumas (pritaikykite pagal laikomus laukus)
db.Matches.createIndex(
  { sport: 1, matchType: 1, date: 1, "comand1.name": 1, "comand2.name": 1 },
  { unique: true }
)

// Bets
db.Bets.createIndex({ userEmail: 1 })
db.Bets.createIndex({ status: 1 })
db.Bets.createIndex({ "event.date": -1 })
db.Bets.createIndex({ "event.team_1": 1 })
db.Bets.createIndex({ "event.team_2": 1 })
// Unikalus (dublikato prevencija):
db.Bets.createIndex(
  { userEmail: 1, "bet.choice": 1, "event.team_1": 1, "event.team_2": 1, "event.date": 1 },
  { unique: true }
)
```

---

## Duomenų schemų pavyzdžiai

**Users**
```json
{
  "_id": "64f...",
  "email": "user@example.com",
  "firstName": "Jonas",
  "lastName": "Jonaitis",
  "nickname": "jj",
  "phone": "+370...",
  "IBAN": "LT...",
  "balance": "123.45",                // saugoma kaip Decimal128; atsakyme - string
  "birthDate": "1990-01-01T00:00:00Z",
  "createdAt": "2025-01-15T10:10:10Z",
  "updatedAt": "2025-01-20T08:00:00Z"
}
```

**Teams**
```json
{
  "_id": "65a...",
  "teamName": "Žalgiris",
  "sport": "basketball",
  "rating": 95,
  "players": [
    { "name": "...", "achievements": { "careerGoalsOrPoints": 123, "penaltiesReceived": 11 } }
  ],
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-05T00:00:00Z"
}
```

**Matches**
```json
{
  "_id": "65b...",
  "sport": "krepsinis",
  "matchType": "league",
  "date": "2025-09-05T19:00:00Z",
  "comand1": { "name": "Žalgiris", ... },
  "comand2": { "name": "Rytas", ... },
  "created_at": "...",
  "updated_at": "..."
}
```

**Bets**
```json
{
  "_id": "65c...",
  "userEmail": "user@example.com",
  "userId": "64f...",
  "event": {
    "team_1": "Zalgiris",
    "team_2": "Rytas",
    "type": "final",
    "date": "2025-09-05"   // arba Date (rekomenduojama vienodinti)
  },
  "bet": {
    "choice": "winner",
    "team": "Zalgiris",
    "stake": "10.00",      // Decimal128 → atsakyme string
    "odds": 1.85
  },
  "status": "pending",
  "createdAt": "2025-09-01T12:00:00Z",
  "updatedAt": "2025-09-01T12:34:56Z"
}
```

---

## Pastabos apie apsaugą
- Šiuo metu autentifikacijos/autorziacijos sluoksnis nenumatytas — pridėkite pagal poreikį (API key/JWT, rate limiting).
- Validuokite įvestis (regex injekcijų prevencija: `re.escape` arba neatviri `$regex`).
- Nenaudokite slaptažodžių/tokenų laukuose atsakymuose (naudokite **projection**, pvz., `{"password": 0}`).
- Loguokite settlement operacijas (ledger) su `operationId` idempotencijai (ypač integruojant mokėjimus/webhook).

---

## Greiti cURL pavyzdžiai

**Sukurti vartotoją**
```bash
curl -X POST http://localhost:5000/users -H "Content-Type: application/json" -d '{
  "email": "user@example.com",
  "nickname": "jj",
  "firstName": "Jonas",
  "lastName": "Jonaitis",
  "phone": "+37061234567",
  "IBAN": "LT12...",
  "balance": "50.00"
}'
```

**Padidinti balansą +12.50**
```bash
curl -X POST http://localhost:5000/users/increment_balance -H "Content-Type: application/json" -d '{
  "userId": "64f...",
  "delta": "12.50"
}'
```

**Sukurti statymą**
```bash
curl -X POST http://localhost:5000/bets -H "Content-Type: application/json" -d '{
  "userEmail": "user@example.com",
  "userId": "64f...",
  "event": {"team_1": "Zalgiris", "team_2": "Rytas", "type": "final", "date": "2025-09-05"},
  "bet": {"choice": "winner", "team": "Zalgiris", "stake": "10.00", "odds": 1.85},
  "status": "pending"
}'
```

**Atnaujinti statymo statusą į `won` (su settlement)**
```bash
curl -X POST http://localhost:5000/bets/update_status -H "Content-Type: application/json" -d '{
  "betId": "65c...",
  "status": "won"
}'
```

**Gauti statymus su filtrais**
```bash
curl "http://localhost:5000/bets?status=pending&team=Zalgiris&event_start_date=2025-09-01&event_end_date=2025-09-30&limit=50&skip=0"
```

---

### Pastaba
Jeigu kuri nors konkreti realizacija jūsų kode skiriasi (pavyzdžiui, `event.date` laikote **tik `Date`**), naudokite dokumente atitinkamą dalį ir išmeskite nebereikalingą „string“ atšaką. Šis README sukomponuotas taip, kad atitiktų jūsų turimą API ir rekomenduojamą gerąją praktiką.
