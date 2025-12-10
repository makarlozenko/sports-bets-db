📥 Sukurti reikalingus indeksus Elasticsearch
POST http://127.0.0.1:5000/es/init

✔ Galimas atsakymas:
{
  "status": "ok",
  "indexes": {
    "matches_search": "ready",
    "bets_analytics": "ready"
  }
}

🔄 3. Duomenų sinchronizavimas

Jeigu MongoDB jau turi duomenų — juos galima sukelti į Elasticsearch.

📌 Sinchronizuoti visus match'us
POST http://127.0.0.1:5000/es/sync/matches


Atsakymas:

{
  "status": "ok",
  "indexed": 8
}

📌 Sinchronizuoti visas lažybas (bets)
POST http://127.0.0.1:5000/es/sync/bets


Atsakymas:

{
  "status": "ok",
  "indexed": 14
}

🔍 4. Paieškos API

Sukurtas backend paieškos endpoint'as leidžia filtruoti match'us pagal komandą, sporto tipą, datas ir kitus kriterijus.

🔎 4.1 Ieškoti rungtynių pagal komandą
GET http://127.0.0.1:5000/search/matches?team=Vilnius

✔ Pavyzdinis atsakymas:
{
  "total": 4,
  "items": [
    {
      "match_id": "68e7b61f...",
      "sport": "football",
      "teams": "Vilnius FC vs Kaunas United",
      "date": "2025-08-15",
      "matchType": "league",
      "score": 0.11431682
    }
  ]
}

🏟 4.2 Filtracija pagal datą
GET http://127.0.0.1:5000/search/matches?from=2025-09-01&to=2025-12-31


Atsakymas gali atrodyti taip:

{
  "total": 8,
  "items": [
    {
      "teams": "Vilnius Wolves vs Kaunas Green",
      "date": "2025-09-01",
      "sport": "basketball",
      "match_id": "68e7b61f...",
      "score": 0.0
    }
  ]
}

✨ 5. Autocomplete (komandų pasiūlymai)
GET http://127.0.0.1:5000/search/teams?q=Vi


Atsakymo pavyzdys:

{
  "query": "Vi",
  "teams": [
    "Vilnius FC",
    "Vilnius Wolves"
  ]
}


Tai naudojama automatinėms paieškos užuominoms (kaip Google auto-suggest).

🔎 6. Elasticsearch rankinis testavimas (optional)
📌 Per Kibana Dev Tools arba terminalą
Gauti visus match’us:
curl "http://localhost:9200/matches_search/_search?pretty"

Ieškoti pagal komandą:
curl "http://localhost:9200/matches_search/_search?q=teams:Vilnius&pretty"