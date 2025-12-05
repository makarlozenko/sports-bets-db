import requests
import json
import time

BASE_URL = "http://127.0.0.1:5000"
USER_EMAIL = "arina.ti@outlook.com"

def pretty(label, resp):
    print("\n" + label + ":")
    print(json.dumps(resp, indent=2))


def fetch_recommendations(stage_label):
    url = f"{BASE_URL}/neo4j/recommend/matches/{USER_EMAIL}"
    resp = requests.get(url).json()
    pretty(stage_label, resp)

def fetch_similar_users(stage_label):
    url = f"{BASE_URL}/neo4j/user/{USER_EMAIL}/similar"
    resp = requests.get(url).json()
    pretty(stage_label, resp)


match1 = {
    "sport": "basketball",
    "matchType": "league",
    "date": "2025-12-09",
    "team1": {"name": "Vilnius Wolves"},
    "team2": {"name": "Kaunas Green"}
}

match2 = {
    "sport": "basketball",
    "matchType": "league",
    "date": "2025-12-10",
    "team1": {"name": "Vilnius Wolves"},
    "team2": {"name": "Kaunas Green"}
}

match3 = {
    "sport": "basketball",
    "matchType": "league",
    "date": "2025-12-12",
    "team1": {"name": "Vilnius Wolves"},
    "team2": {"name": "Kaunas Green"}
}

match4 = {
    "sport": "basketball",
    "matchType": "league",
    "date": "2025-12-15",
    "team1": {"name": "Kaunas Green"},
    "team2": {"name": "Panevezys Town"}
}

all_matches = [match1, match2, match3, match4]

created_ids = []

for i, m in enumerate(all_matches, start=1):
    resp = requests.post(f"{BASE_URL}/matches", json=m).json()
    pretty(f"Created match {i}", resp)

    if "match" in resp and "_id" in resp["match"]:
        created_ids.append(resp["match"]["_id"])
    else:
        print("ERROR: match did not return an _id")

print("\nCreated match IDs:", created_ids)

fetch_similar_users("Similar users by bets")
fetch_recommendations("Recommendations after creating matches")

for match_id in created_ids:
    delete_resp = requests.delete(f"{BASE_URL}/matches/{match_id}")
    print(f"Deleted match {match_id}: {delete_resp.status_code}")

print("\nAll created matches deleted.")

fetch_recommendations("Recommendations after deleting matches:")

print("\nDone.")
