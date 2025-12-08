# README — Elasticsearch Integration for SportBET Project

## 1. Overview
This document describes how Elasticsearch was integrated into the SportBET project as a secondary analytical/search database.  
The integration includes:

- Running Elasticsearch + Kibana via Docker  
- Real-time indexing of Matches and Bets from MongoDB  
- REST endpoints for initializing indices and searching  
- Tools for verifying synchronization in Kibana  
- Full recovery mechanism (`/es/init`)

This README is fully technical and intended for deployment, debugging, and university review.

---

## 2. Requirements

Before starting, install:

✅ **Docker Desktop**  
https://www.docker.com/products/docker-desktop/

⚠️ *Important:* Docker Desktop uses WSL2 backend, meaning memory and CPU limits are controlled by Windows.

---

## 3. Configure WSL2 Memory (Required for Elasticsearch)

Elasticsearch needs at least **4GB RAM**.

To avoid container crashes, configure WSL2 resources.

File:  
```
C:\Users\<YourUser>\.wslconfig
```

If file doesn’t exist — create it.

Paste:

```
[wsl2]
memory=8GB
processors=4
swap=2GB
localhostForwarding=true
```

Restart WSL:

```
wsl --shutdown
```

Restart Docker Desktop.

---

## 4. Start Elasticsearch + Kibana Containers

**docker-compose.yml:**

```yaml
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.10.2
    container_name: elasticsearch
    ports:
      - "9200:9200"
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:9200 || exit 1"]
      interval: 30s
      timeout: 20s
      retries: 3

  kibana:
    image: docker.elastic.co/kibana/kibana:8.10.2
    container_name: kibana
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch
```

Start:

```
docker compose up -d
```

Verify:

```
docker ps
```

Check Elasticsearch cluster:

```
curl http://localhost:9200
```

Open Kibana:

👉 http://localhost:5601

---

## 5. Python Elastic Client

`elasticsearch_client.py`:

```python
from elasticsearch import Elasticsearch

ES_URL = "http://localhost:9200"

es = Elasticsearch(
    ES_URL,
    verify_certs=False
)

def test_es_connection():
    try:
        if es.ping():
            print("Elasticsearch is UP")
            info = es.info()
            print("Cluster:", info['cluster_name'])
            print("Version:", info['version']['number'])
        else:
            print("Elasticsearch is DOWN")
    except Exception as e:
        print("ES CONNECTION ERROR:", e)
```

Used in `main.py`:

```python
from elasticsearch_client import es, test_es_connection
test_es_connection()
```

---

## 6. Index Initialization Endpoint

Endpoint:

```
POST /es/init
```

Creates two indices:

- `bets`
- `matches`

Example response:

```json
{
  "status": "ok",
  "indexes": {
    "bets": { "status": "exists" },
    "matches": { "status": "exists" }
  }
}
```

---

## 7. Index Mappings

### matches index

Stores:

- sport  
- matchType  
- date  
- team1, team2  

Mapping:

```json
{
  "mappings": {
    "properties": {
      "sport": { "type": "keyword" },
      "matchType": { "type": "keyword" },
      "team1": { "type": "keyword" },
      "team2": { "type": "keyword" },
      "date": { "type": "date" }
    }
  }
}
```

### bets index

Stores:

- userEmail  
- choice  
- stake  
- team bet_on  
- sport  
- match date  

---

## 8. Real-Time Syncing

When a new Match or Bet is created:

```python
es.index(index="matches", id=<mongodb_id>, document=...)
es.index(index="bets", id=<mongodb_id>, document=...)
```

Elasticsearch always mirrors MongoDB.

---

## 9. Checking Data in Kibana

Open:

👉 http://localhost:5601

Then:

**Discover → Create index pattern**

Patterns:

- `matches*`
- `bets*`

Select timestamp: `date`.

---

## 10. Kibana Dev Tools Queries

Fetch all matches:

```
GET matches/_search
{
  "query": { "match_all": {} }
}
```

Search by team:

```
GET matches/_search
{
  "query": {
    "multi_match": {
      "query": "Vilnius",
      "fields": ["team1", "team2"]
    }
  }
}
```

---

## 11. Postman Testing

Re-init ES:

```
POST /es/init
```

Create match:

```
POST /matches
```

Create bet:

```
POST /bets
```

Check Kibana — data appears instantly.

---

## 12. Complete Run Order

1. Start Docker Desktop  
2. Ensure WSL2 RAM config  
3. Run containers:  
   ```
   docker compose up -d
   ```
4. Start Python backend:  
   ```
   python main.py
   ```
5. Initialize ES:  
   ```
   POST /es/init
   ```
6. Create match/bet  
7. Verify in Kibana  

---

## 13. Troubleshooting

❌ **Elasticsearch DOWN**  
Cause: Not enough RAM  
Fix: Configure `.wslconfig`

---

## 14. Conclusion

You now have:

- Elasticsearch running in Docker  
- Kibana UI  
- Full Python integration  
- Real-time sync from MongoDB  
- `/es/init` full recovery  
- Search API ready  

✔ fulfills all assignment requirements.
