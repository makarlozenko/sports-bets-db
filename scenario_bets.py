#!/usr/bin/env python3
"""
Auto-settle bets when match has finished:
- Compares user's choice with actual match result (score or team)
- Updates bet status (pending -> won/lose)
- Updates user balance accordingly.
"""

import sys
from datetime import datetime
import requests

BASE_URL = "http://127.0.0.1:5000"

def get_json(resp):
    try:
        return resp.json()
    except:
        return {"raw_text": resp.text}

def get_pending_bets():
    url = f"{BASE_URL}/bets?status=pending"
    resp = requests.get(url, timeout=30)
    return get_json(resp).get("items", [])

def get_matches():
    url = f"{BASE_URL}/matches"
    resp = requests.get(url, timeout=30)
    return get_json(resp).get("items", [])

def get_user_by_id(user_id):
    url = f"{BASE_URL}/users/{user_id}"
    resp = requests.get(url, timeout=30)
    data = get_json(resp)
    return data.get("user")

def update_bet_status(bet_id, new_status):
    url = f"{BASE_URL}/bets/{bet_id}"
    resp = requests.patch(url, json={"status": new_status}, timeout=30)
    if resp.status_code not in (200, 204):
        print(f"⚠️ PATCH failed for bet {bet_id}: {resp.status_code}, {resp.text}")
    return get_json(resp)

def update_user_balance(user_id, new_balance):
    url = f"{BASE_URL}/users/{user_id}"
    resp = requests.patch(url, json={"balance": new_balance}, timeout=30)
    if resp.status_code not in (200, 204):
        print(f"⚠️ PATCH failed for user {user_id}: {resp.status_code}, {resp.text}")
    return get_json(resp)

def parse_date(d):
    """Different formats of dates"""
    for fmt in ("%a, %d %b %Y %H:%M:%S %Z", "%Y-%m-%d"):
        try:
            return datetime.strptime(d, fmt)
        except:
            continue
    return None

def find_match_for_bet(bet, matches):
    bet_date = parse_date(bet["event"]["date"])
    team1 = bet["event"]["team_1"]
    team2 = bet["event"]["team_2"]

    for m in matches:
        match_date = parse_date(m.get("date"))
        kom1 = m["comand1"]["name"]
        kom2 = m["comand2"]["name"]

        if match_date == bet_date and team1 == kom1 and team2 == kom2:
            return m
    return None

def get_match_result(match):
    """
    Returns winner and match score
    """
    t1 = match["comand1"]["name"]
    t2 = match["comand2"]["name"]

    r1 = match["comand1"].get("result", {})
    r2 = match["comand2"].get("result", {})

    winner = None
    if r1.get("status") == "won":
        winner = t1
    elif r2.get("status") == "won":
        winner = t2
    elif r1.get("status") == "draw" or r2.get("status") == "draw":
        winner = "draw"

    score = (r1.get("goalsFor"), r2.get("goalsFor"))
    return winner, score

def main():
    print("=== STARTING BETS UPDATE SCENARIO ===")
    today = datetime.now()
    bets = get_pending_bets()
    matches = get_matches()

    for bet in bets:
        match = find_match_for_bet(bet, matches)
        if not match:
            print(f"⚠️ No match found for bet {bet['_id']} ({bet['event']['team_1']}, {bet['event']['team_2']}, {bet['event']['date']})")
            continue

        match_date = parse_date(match.get("date"))
        if not match_date:
            print(f"⚠️ Cannot parse match date for {bet['_id']}")
            continue

        if match_date > today:
            #Match not played yet
            continue

        # Getting result
        winner, score = get_match_result(match)

        # Determining status of bet
        status = "lost"
        if bet["bet"]["choice"] == "winner":
            if bet["bet"].get("team") == winner:
                status = "won"
            elif winner == "draw" and bet["bet"].get("team") == "draw":
                status = "won"
        elif bet["bet"]["choice"] == "score":
            bet_score = bet["bet"].get("score", {})
            if (bet_score.get("team_1") == score[0] and bet_score.get("team_2") == score[1]):
                status = "won"

        # Updating bet through patch
        update_bet_status(bet["_id"], status)
        print(f"✅ Bet {bet['_id']} updated -> {status}")

        # Updating balance through userId
        user_id = bet.get("userId")
        user = get_user_by_id(user_id)
        if not user:
            print(f"⚠️ User {user_id} not found")
            continue

        balance = float(user.get("balance", 0))
        stake = float(bet["bet"]["stake"])
        odds = float(bet["bet"].get("odds", 1))
        if status == "won":
            balance += stake * odds
        else:
            balance -= stake

        update_user_balance(user["_id"], balance)
        print(f"💰 User {user['email']} balance updated -> {balance:.2f}")

    print("=== FINISHED ===")

if __name__ == "__main__":
    sys.exit(main())


# {
#             "_id": "68e7b61ff2656d90ad339dd6",
#             "comand1": {
#                 "name": "Vilnius FC",
#                 "result": {
#                     "cards": {
#                         "red": 1,
#                         "yellow": 0
#                     },
#                     "goalsAgainst": 3,
#                     "goalsFor": 1,
#                     "status": "lost"
#                 }
#             },
#             "comand2": {
#                 "name": "Siauliai Stars",
#                 "result": {
#                     "cards": {
#                         "red": 0,
#                         "yellow": 0
#                     },
#                     "goalsAgainst": 1,
#                     "goalsFor": 3,
#                     "status": "won"
#                 }
#             },
#             "date": "2025-09-05",
#             "matchType": "league",
#             "sport": "football"
#         },


# {
#             "_id": "9e810caf0c85f9e99457b868",
#             "bet": {
#                 "choice": "winner",
#                 "createdAt": "Tue, 02 Jul 2025 00:00:00 GMT",
#                 "odds": 2.38,
#                 "stake": 28.76,
#                 "team": "Vilnius FC"
#             },
#             "event": {
#                 "date": "Fri, 03 Oct 2025 00:00:00 GMT",
#                 "team_1": "Vilnius FC",
#                 "team_2": "Siauliai Stars",
#                 "type": "league"
#             },
#             "status": "pending",
#             "userEmail": "tomas.sadauskas3@gmail.com",
#             "userId": "c071c814fe9cdca5ef9eda76"
#         },


