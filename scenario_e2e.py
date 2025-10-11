
"""
Scenario (end-to-end):
Flow:
1) GET /bets/summary -> print summary for the chosen user (BEFORE)
2) POST /matches     -> create a new match (print what was created)
3) POST /bets        -> create a new bet for that user (print what was created)
4) GET /bets/summary -> print summary for the same user (AFTER) + show deltas
5) DELETE /bets/<id> -> clean up the just-created bet
"""

import sys
import json
import time
from typing import Any, Dict, Optional
import requests

# ========= CONFIG =========
BASE_URL = "http://127.0.0.1:5050"
USER_EMAIL = "aurimas.mikalauskas14@gmail.com"  # existing user in DB

# teams/date consistent between match and bet
TEAM_1 = "Kaunas United"
TEAM_2 = "Klaipeda City"
MATCH_DATE = "2025-10-08"  # YYYY-MM-DD

# Example match payload
match_payload = {
  "matchType": "league",
  "sport": "football",
  "date": MATCH_DATE,
  "comand1": {
    "name": TEAM_1,
    "result": {
      "status": "won",
      "goalsFor": 2,
      "goalsAgainst": 1,
      "cards": {"red": 0, "yellow": 2}
    }
  },
  "comand2": {
    "name": TEAM_2,
    "result": {
      "status": "lost",
      "goalsFor": 1,
      "goalsAgainst": 2,
      "cards": {"red": 0, "yellow": 1}
    }
  }
}

# Example bet payload (for the same user and same event as the match)
bet_payload = {
    "userEmail": USER_EMAIL,
    "event": {
        "team_1": TEAM_1,
        "team_2": TEAM_2,
        "date": MATCH_DATE
    },
    "bet": {
            "choice": "winner",
            "team": TEAM_1,
            "odds": 2.0,
            "stake": 50.0
    },
    "status": "won"
}

# =========================

def pretty(title: str, data: Any) -> None:
    print("\n" + "="*len(title))
    print(title)
    print("="*len(title))
    if isinstance(data, (dict, list)):
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(data)

def get_json(resp: requests.Response) -> Any:
    try:
        return resp.json()
    except Exception:
        return {"raw_text": resp.text}

def get_user_summary(email: str) -> Optional[Dict[str, Any]]:
    """Return the single summary row for the user
    (userEmail, total_won, total_lost, final_balance) or None."""
    url = f"{BASE_URL}/bets/summary"
    resp = requests.get(url, timeout=30)
    data = get_json(resp)
    if isinstance(data, list):
        for row in data:
            if isinstance(row, dict) and row.get("userEmail") == email:
                return row
    return None

def post_match(payload: Dict[str, Any]) -> Dict[str, Any]:
    """POST /matches"""
    url = f"{BASE_URL}/matches"
    resp = requests.post(url, json=payload, timeout=30)
    return get_json(resp)

def post_bet(payload: Dict[str, Any]) -> Dict[str, Any]:
    """POST /bets; returns response JSON with 'bet' if success."""
    url = f"{BASE_URL}/bets"
    resp = requests.post(url, json=payload, timeout=30)
    return get_json(resp)

def delete_bet(bet_id: str) -> Dict[str, Any]:
    """DELETE /bets/<bet_id>"""
    url = f"{BASE_URL}/bets/{bet_id}"
    resp = requests.delete(url, timeout=30)
    return get_json(resp)

def extract_bet_id(bet_response: Any) -> Optional[str]:
    # Expecting {"message": "...", "bet": {..., "_id": "..."}}
    if isinstance(bet_response, dict):
        bet = bet_response.get("bet")
        if isinstance(bet, dict):
            return bet.get("_id")
    return None

def main() -> int:
    print("Running E2E scenario against:", BASE_URL)
    print("User:", USER_EMAIL)

    # 1) Summary BEFORE
    before = get_user_summary(USER_EMAIL)
    if before:
        pretty(f"User summary BEFORE for {USER_EMAIL}", before)
    else:
        pretty(f"User summary BEFORE for {USER_EMAIL}", "No summary row found (maybe no settled bets yet).")

    # 2) Create a MATCH
    match_resp = post_match(match_payload)
    pretty("Created match (response)", match_resp)

    # 3) Create a BET for this user
    bet_resp = post_bet(bet_payload)
    pretty("Created bet (response)", bet_resp)

    # Capture created bet id for cleanup
    bet_id = extract_bet_id(bet_resp)
    if not bet_id:
        print("⚠️ Could not find bet _id in response; cleanup may be skipped.")

    # 4) Summary AFTER
    # wait a moment to let the write become visible
    time.sleep(0.5)
    after = get_user_summary(USER_EMAIL)
    if after:
        pretty(f"User summary AFTER for {USER_EMAIL}", after)
    else:
        pretty(f"User summary AFTER for {USER_EMAIL}", "No summary row found.")

    # Show deltas if possible
    def to_num(x):
        try:
            return float(x)
        except Exception:
            return None

    if before and after:
        keys = ["total_won", "total_lost", "final_balance"]
        deltas = {}
        for k in keys:
            b = to_num(before.get(k))
            a = to_num(after.get(k))
            deltas[k] = (None if b is None or a is None else round(a - b, 4))
        pretty("Summary deltas (AFTER - BEFORE)", deltas)

    # 5) Cleanup: delete the just-created bet
    if bet_id:
        del_resp = delete_bet(bet_id)
        pretty("Deleted bet (response)", del_resp)
    else:
        print("ℹ️ Skipping delete; no bet_id found.")

    print("\nDone.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
