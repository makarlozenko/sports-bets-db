# README — Elasticsearch Integration for SportBET Project

## 1. Overview
This document describes how Elasticsearch was integrated into the SportBET project as a secondary analytical/search database.  

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
C:\Users\Admin\.wslconfig
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

Restart WSL (Run PowerShell as Administrator):

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

Start (In the PowerShell in the project folder):

```
docker compose up -d
```

Verify:

```
docker ps
```

Check Elasticsearch cluster:

```
http://localhost:9200
```

Open Kibana:
```
http://localhost:5601
```
---


## 5. Index Initialization Endpoint

Endpoint:

```
POST http://127.0.0.1:5000/es/init
```

Creates two indices:

- `bets_analytics`
- `matches_search`

Example response:

```json
{
  "status": "ok",
  "indexes": {
    "matches_search": "ready",
    "bets_analytics": "ready"
  }
}
```

---

## 6. Index Mappings

Endpoint:

```
POST http://127.0.0.1:5000/es/reset
```
Deletes AND recreates all indexes.

Endpoint:

```
POST http://127.0.0.1:5000/es/sync/matches
```
Indexes all existing MongoDB matches into ES.
If a new match will be created - it will be automatically indexed.
Example response:

```json
{
 "status": "ok",
 "indexed": 8
}
```

Endpoint:

```
POST http://127.0.0.1:5000/es/sync/bets
```
Indexes all existing MongoDB bets into ES.
If a new bet will be created - it will be automatically indexed.
Example response:

```json
{
 "status": "ok",
 "indexed": 14
}
```

## 7. Kibana: Testing Indexes

Open:

👉 http://localhost:5601

Then:

**Discover → Create index pattern**
Names:

- `matches_search`
- `bets_analytics`
  
Patterns:

- `matches*`
- `bets*`

Select timestamp: `date`.

Go to:

Analytics → Discover → Select index: matches_search

Or test Elasticsearch manually in PowerShell in the project folder.
Indexed matches:
```bash
curl.exe -X GET "http://localhost:9200/matches_search/_search?pretty"
```
Search by team:
```bash
curl.exe -X GET "http://localhost:9200/matches_search/_search?q=teams:Vilnius&pretty"
```
Indexed bets:
```bash
curl.exe -X GET "http://localhost:9200/bets_analytics/_search?pretty"
```
---

## 8. Complete Run Order

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


✔ fulfills all assignment requirements.
