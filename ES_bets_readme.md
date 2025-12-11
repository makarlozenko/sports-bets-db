
# 📘 BETS – Elasticsearch Endpointai

*Statymų (BETS) sinchronizacijos ir analitikos API dokumentacija*

Šis dokumentas aprašo **visus endpointus**, susijusius su:

* `bets_analytics` Elasticsearch indeksu
* statymų (bets) duomenų sinchronizacija
* analitinėmis ataskaitomis (`daily-revenue`, `sport-popularity`)

---

# 🗂 Elasticsearch indeksai

## 🎯 `bets_analytics`

Naudojamas:

* ataskaitoms
* statymų analitikai
* KPI rodikliams

### Indekso mapping (santrauka)

| Laukas      | Tipas   | Aprašymas                 |
| ----------- | ------- | ------------------------- |
| `bet_id`    | keyword | statymo ID                |
| `user`      | keyword | vartotojo el. paštas      |
| `team`      | keyword | pasirinkta komanda        |
| `match_id`  | keyword | susieto match ID          |
| `status`    | keyword | pending / won / lost      |
| `isWin`     | boolean | ar statymas buvo laimėtas |
| `stake`     | float   | statyto suma              |
| `odds`      | float   | koeficientas              |
| `payout`    | float   | laimėjimas                |
| `sport`     | keyword | sporto šaka               |
| `createdAt` | date    | statymo laikas            |

---

# 🚀 Elasticsearch valdymo endpointai

## 🟦 1. **Sukurti indeksus**

### `POST /es/init`

Sukuria `bets_analytics` (ir kitus ES indeksus, jei reikalingi) jei jie neegzistuoja.

**Naudojama:**

* po pirmo projekto paleidimo
* kai trūksta indekso
* testuojant

**Atsakymo pavyzdys:**

```json
{
  "status": "ok",
  "indexes": {
    "bets_analytics": "ready"
  }
}
```

---

## 🟥 2. **Išvalyti ir sukurti indeksus iš naujo**

### `POST /es/reset`

* ištrina indeksą `bets_analytics`
* sukuria iš naujo su mapping

⚠ **Svarbu:** po reset indeksas bus tuščias — reikia perindeksuoti.

**Atsakymo pavyzdys:**

```json
{
  "status": "reset_ok",
  "indexes": {
    "bets_analytics": "ready"
  }
}
```

---

## 🔄 3. **Pilnas BETS perindeksavimas**

### `POST /admin/reindex/bets`

Pilnai atkuria **visą `bets_analytics` indeksą iš MongoDB**:

* ištrina seną indeksą
* sukuria naują su mapping
* užpildo **visais statymais**
* kiekvieną statymą praturtina:

  * `isWin`
  * `payout`
  * `sport`
  * `stake`, `odds`
  * susieto match duomenimis

**Naudojama:**

* pakeitus analitinį modelį
* pakeitus payout logiką
* po serverio atstatymo
* testuojant analitikos funkcionalumą

**Atsakymo pavyzdys:**

```json
{
  "status": "ok",
  "reindexed": 157
}
```

---

## 🔁 4. **Sinchronizuoti visus BETS (be drop)**

### `POST /es/sync/bets`

Perrašo **visus** MongoDB statymus į `bets_analytics`, bet:

* neištrina indekso
* neišvalo dokumentų
* tiesiog atnaujina/įterpia

**Naudojama:**

* kai reikia atnaujinti duomenis neištrinant indekso
* kai ES prarado dalį dokumentų
* kai tikrinama sinchronizacijos funkcija

**Atsakymo pavyzdys:**

```json
{
  "status": "ok",
  "indexed": 157
}
```

---

# 📊 Analitiniai Elasticsearch endpointai

Analitiniai endpointai **nuskaito duomenis tik iš `bets_analytics`**.

---

## 📈 5. Dienos pajamų ataskaita

### `GET /reports/daily-revenue`

Apskaičiuoja:

* bendras statytas sumas
* bendras išmokas
* pelną/nuostolį
* statymų skaičių
* grupavimas per dieną

**Query parametrai:**

| Parametras | Aprašymas                  |
| ---------- | -------------------------- |
| `from`     | pradžios data (YYYY-MM-DD) |
| `to`       | pabaigos data (YYYY-MM-DD) |

**Atsakymas:**

```json
[
  {
    "date": "2025-01-15",
    "total_stake": 200.00,
    "total_payout": 350.00,
    "bet_count": 12
  }
]
```

---

## 📊 6. Sporto populiarumo statistika

### `GET /reports/sport-popularity`

Grąžina populiariausias sporto šakas:

* statymų skaičių
* bendrą statytą sumą
* bendrą išmokėjimo sumą

**Query parametrai:**

| Parametras | Aprašymas     |
| ---------- | ------------- |
| `from`     | pradžios data |
| `to`       | pabaigos data |

**Atsakymas:**

```json
[
  {
    "sport": "football",
    "bet_count": 42,
    "total_stake": 610.0,
    "total_payout": 480.0
  }
]
```

---

# 🧪 Testavimo planas

### ✔ 1. Inicializuoti indeksą

```bash
POST /es/init
```

### ✔ 2. Sukurti kelis statymus (`POST /bets`)

### ✔ 3. Patikrinti, kad jie yra Elasticsearch

```bash
GET /reports/daily-revenue
GET /reports/sport-popularity
```

### ✔ 4. Patikrinti reindeksavimą

```bash
POST /admin/reindex/bets
```

### ✔ 5. Patikrinti, kad analitika atsistato teisingai

---
