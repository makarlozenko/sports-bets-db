import requests
import json

BASE_URL = "http://127.0.0.1:5000"



# --- Bet data ---
bet1_data = {
    "userId": "20ba1f0e3b20a2c5dcce32d6",
    "userEmail": "rytis.jankauskas13@gmail.com",
    "event": {
        "team_1": "Vilnius FC",
        "team_2": "Kaunas United",
        "type": "league",
        "date": "2025-08-15"
    },
    "bet": {
        "choice": "winner",
        "team": "Kaunas United",
        "odds": 2.0,
        "stake": 10.0
    }
}

bet2_data = {
    "userId": "20ba1f0e3b20a2c5dcce32d6",
    "userEmail": "rytis.jankauskas13@gmail.com",
    "event": {
        "team_1": "Vilnius Wolves",
        "team_2": "Panevezys Titans",
        "type": "league",
        "date": "2025-10-06"
    },
    "bet": {
        "choice": "score",
        "score": {
            "team_1": 90,
            "team_2": 75
        },
        "odds": 2.0,
        "stake": 10.0
    }
}

# --- Post bets ---
bet1_resp = requests.post(f"{BASE_URL}/bets", json=bet1_data).json()
bet2_resp = requests.post(f"{BASE_URL}/bets", json=bet2_data).json()

print("Bet 1 created:", bet1_resp)
print("Bet 2 created:", bet2_resp)

# --- Extract bet IDs ---
bet1_id = bet1_resp['bet']['_id']
bet2_id = bet2_resp['bet']['_id']

# --- Fetch Neo4j bets for the user ---
neo4j_bets_before = requests.get(f"{BASE_URL}/neo4j/by_user/rytis.jankauskas13@gmail.com/bets").json()
print("\nNeo4j bets for user after creation:")
print(json.dumps(neo4j_bets_before, indent=2))

# --- Delete bets ---
requests.delete(f"{BASE_URL}/bets/{bet1_id}")
requests.delete(f"{BASE_URL}/bets/{bet2_id}")

# --- Fetch Neo4j bets for the user again ---
neo4j_bets_after = requests.get(f"{BASE_URL}/neo4j/by_user/rytis.jankauskas13@gmail.com/bets").json()
print("\nNeo4j bets for user after deletion:")
print(json.dumps(neo4j_bets_after, indent=2))