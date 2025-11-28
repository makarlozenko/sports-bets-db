import requests
import json

BASE_URL = "http://127.0.0.1:5000"

bet1_data = {
    "userId": "327dff8b4f0efe26ea730666",
    "userEmail": "paulius.grabauskas7@outlook.com",
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
    "userId": "3b43df693db1b3fec4f1746b",
    "userEmail": "deividas.kazlauskas8@outlook.com",
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

# --- Create bets ---
bet1_resp = requests.post(f"{BASE_URL}/bets", json=bet1_data).json()
bet2_resp = requests.post(f"{BASE_URL}/bets", json=bet2_data).json()

print("Bet 1 created:", bet1_resp)
print("Bet 2 created:", bet2_resp)

# Safety
if "bet" not in bet1_resp or "bet" not in bet2_resp:
    print("One or both bets not created.")
    print("Bet1:", bet1_resp)
    print("Bet2:", bet2_resp)
    exit(1)

bet1_id = bet1_resp["bet"]["_id"]
bet2_id = bet2_resp["bet"]["_id"]

# --- Check Neo4J BEFORE deletion ---
print("\nNeo4J data for Paulius:")
neo_before_1 = requests.get(f"{BASE_URL}/neo4j/by_user/{bet1_data['userEmail']}/bets").json()
print(json.dumps(neo_before_1, indent=2))

print("\nNeo4J data for Deividas:")
neo_before_2 = requests.get(f"{BASE_URL}/neo4j/by_user/{bet2_data['userEmail']}/bets").json()
print(json.dumps(neo_before_2, indent=2))

# --- Delete both bets ---
requests.delete(f"{BASE_URL}/bets/{bet1_id}")
requests.delete(f"{BASE_URL}/bets/{bet2_id}")

print("\nNeo4J AFTER deletion:")

neo_after_1 = requests.get(f"{BASE_URL}/neo4j/by_user/{bet1_data['userEmail']}/bets").json()
print("Paulius:", json.dumps(neo_after_1, indent=2))

neo_after_2 = requests.get(f"{BASE_URL}/neo4j/by_user/{bet2_data['userEmail']}/bets").json()
print("Deividas:", json.dumps(neo_after_2, indent=2))
