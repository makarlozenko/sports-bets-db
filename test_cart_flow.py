import requests
import json
import time
from pprint import pprint
import redis
from pymongo import MongoClient
import certifi


# ---------- Configuration ----------
BASE_URL = "http://127.0.0.1:5000"
USER_EMAIL = "dovydas.sakalauskas5@gmail.com"
USER_ID = "ee576a2c1f82513b2d4b8047"

# Redis connection
r = redis.Redis(host="localhost", port=6379, decode_responses=True)

# Mongo connection
client = MongoClient('mongodb+srv://arinatichonovskaja_db_user:Komanda@sportbet.wafmb2f.mongodb.net/?retryWrites=true&w=majority&appName=SportBet',
                     tlsCAFile=certifi.where())
db = client.SportBET
bets_collection = db.Bets


def print_line(title):
    print("\n" + "=" * 15 + f" {title} " + "=" * 15)


def add_to_cart(event_team1, event_team2, stake):
    """Add one bet item into Redis cart"""
    payload = {
        "userEmail": USER_EMAIL,
        "item": {
            "event": {
                "team_1": event_team1,
                "team_2": event_team2,
                "type": "league",
                "date": "2025-08-29"
            },
            "bet": {
                "choice": "winner",
                "team": event_team2,
                "stake": stake
            }
        }
    }
    resp = requests.post(f"{BASE_URL}/cart/items", json=payload)
    print(f"Added bet {event_team1} vs {event_team2}: {resp.status_code}")
    pprint(resp.json())


def show_redis_state():
    """Display Redis keys, TTL, and content"""
    print_line("REDIS STATE")
    keys = r.keys("app:cart:user:*")
    if not keys:
        print("Redis is empty.")
        return
    for key in keys:
        print(f"Key: {key}")
        print(f"TTL: {r.ttl(key)} seconds")
        data = r.hgetall(key)
        print(f"Items: {len(data)}")
        for k, v in data.items():
            print(f"  {k} → {v[:100]}...")


def show_mongo_state():
    """Show all bets for the test user in MongoDB"""
    print_line("MONGO (user bets)")
    bets = list(bets_collection.find({"userEmail": USER_EMAIL}, {"_id": 0, "event": 1, "bet": 1}))
    print(f"Found {len(bets)} bets:")
    for b in bets:
        pprint(b)


def main():
    print_line("STEP 1 — add two bets into the cart")
    add_to_cart("Vilnius FC", "Panevezys Town", 25)
    add_to_cart("Kaunas United", "Riga City", 40)

    time.sleep(1)
    show_redis_state()

    print_line("STEP 2 — confirm MongoDB is still empty")
    show_mongo_state()

    print_line("STEP 3 — perform checkout (move from Redis → Mongo)")
    payload = {"userEmail": USER_EMAIL}
    resp = requests.post(f"{BASE_URL}/cart/checkout", json=payload)
    print(f"Checkout: {resp.status_code}")
    pprint(resp.json())

    time.sleep(1)
    print_line("STEP 4 — verify Redis is now empty")
    show_redis_state()

    print_line("STEP 5 — verify bets are now in MongoDB")
    show_mongo_state()


if __name__ == "__main__":
    main()
