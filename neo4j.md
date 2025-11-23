# Neo4j integracija (SportBET)

Ši dalis atsakinga už **grafų duomenų bazę** su Neo4j.  
Čia saugomi paprasti pavyzdiniai duomenys (kol kas):
- `User` – vartotojai (Arina, Edvinas)
- `Team` – komandos (Vilnius Wolves, Kaunas Green)
- `Match` – rungtynės (Wolves vs Green)
- `Bet` – statymai 

Visa logika yra faile: **`neo4j_connect.py`**  
Integracija į Flask API daroma faile **`main.py`**.

---

## 1. Reikalavimai

- Python paketai:
  - `neo4j`
  - `flask`
- Turėti veikiančią Neo4j **Aura** duomenų bazę:
  - `URI` : `neo4j+s://37b79b6d.databases.neo4j.io`
  - vartotojas (`neo4j`)
  - slaptažodis (`qCyhqY1TKvwPEKrzECH7N8u-jBJOkH2lkvXQFLQT8c8`)

---

## 2. Ko komandai reikia
Vizualui patogu naudoti aplikaciją, užsikraukite ją: `Neo4j Desktop`,
ten matysite grafus, ryšius ir nodes.

Prisijunkite prie mūsų duombazės:
```python
URI = "neo4j+s://37b79b6d.databases.neo4j.io"
USER = "neo4j"
PASSWORD = "qCyhqY1TKvwPEKrzECH7N8u-jBJOkH2lkvXQFLQT8c8"
```

---