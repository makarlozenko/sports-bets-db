#!/usr/bin/env python3
"""
Automatinis statymų suvedimas:
- Randa 'pending' statymus ir atitinkamas rungtynes
- Palygina vartotojo pasirinktą baigtį su faktiniu rezultatu
- Atnaujina statymo statusą per POST /bets/update_status
- (Pasirinktinai) atnaujina vartotojo balansą (PATCH /users/<id> su fallback į POST /users/update_balance)
"""

import sys
from datetime import datetime
import requests

BASE_URL = "http://127.0.0.1:5050"

# Įjunk/įjunk seedinimą
SEED_BETS = True

#dovydas.sakalauskas5@gmail.com
#ee576a2c1f82513b2d4b8047
# pritaikyk pagal savo vartotoją:
SEED_USER_ID = "dc4e67460108e467079fe68e"
SEED_USER_EMAIL = "martynas.grigonis1@outlook.com"

# ---------- Pagalbinės užklausos ----------
def _safe_json(resp):
    try:
        return resp.json()
    except Exception:
        return {"raw_text": resp.text}

def get_json(resp):
    """Saugiai grąžina JSON iš requests.Response (arba tekstą, jei ne JSON)."""
    try:
        return resp.json()
    except Exception:
        return {"raw_text": resp.text}

def _get(url, **kw):
    resp = requests.get(url, timeout=30, **kw)
    return resp, _safe_json(resp)

def _post(url, json=None, **kw):
    resp = requests.post(url, json=json, timeout=30, **kw)
    return resp, _safe_json(resp)

def _patch(url, json=None, **kw):
    resp = requests.patch(url, json=json, timeout=30, **kw)
    return resp, _safe_json(resp)

# ---------- API kvietimai ----------
def get_pending_bets():
    url = f"{BASE_URL}/bets?status=pending"
    resp, data = _get(url)
    return data.get("items", [])

def get_matches():
    url = f"{BASE_URL}/matches"
    resp, data = _get(url)
    return data.get("items", [])

def get_user_by_id_or_email(user_id, user_email=None):
    """Pirma bando gauti pagal id, jei neranda – bando pagal email (jei pateikta)."""
    if user_id:
        url = f"{BASE_URL}/users/{user_id}"
        resp = requests.get(url, timeout=30)
        if resp.status_code == 200:
            data = get_json(resp)
            return data.get("user") or data
    if user_email:
        url2 = f"{BASE_URL}/users/by_email/{user_email}"
        resp2 = requests.get(url2, timeout=30)
        if resp2.status_code == 200:
            data2 = get_json(resp2)
            return data2.get("user") or data2
    return None

def update_bet_status(bet_id, new_status):
    """
    Naudojam POST /bets/update_status  → body: {"betId": "...", "status": "won"|"lost"}
    (PATCH /bets/<id> pas tave nenumatytas – būtų 405)
    """
    url = f"{BASE_URL}/bets/update_status"
    payload = {"betId": bet_id, "status": new_status}
    resp, data = _post(url, json=payload)
    ok = resp.status_code in (200, 201)
    if not ok:
        print(f"⚠️ Nepavyko atnaujinti statymo {bet_id}: {resp.status_code}, {resp.text}")
    return ok, data

def update_user_balance(user_id, new_balance):
    """Pirma bandom PATCH /users/<id>. Jei nepavyksta – fallback į POST /users/update_balance."""
    # 1) PATCH
    url_patch = f"{BASE_URL}/users/{user_id}"
    resp_patch = requests.patch(url_patch, json={"balance": new_balance}, timeout=30)
    if resp_patch.status_code in (200, 204):
        return True, get_json(resp_patch)

    # 2) Fallback į POST
    url_post = f"{BASE_URL}/users/update_balance"
    resp_post = requests.post(url_post, json={"userId": user_id, "balance": new_balance}, timeout=30)
    if resp_post.status_code in (200, 201):
        return True, get_json(resp_post)

    print(f"⚠️ Balanso atnaujinimas nepavyko vartotojui {user_id}: "
          f"PATCH={resp_patch.status_code} POST={resp_post.status_code}")
    return False, get_json(resp_post)

# ---------- Verslo logika ----------
def parse_date(d):
    """Bandom kelių formatų datas: 'Thu, 03 Oct 2025 00:00:00 GMT' ir 'YYYY-MM-DD'."""
    if d is None:
        return None
    if isinstance(d, datetime):
        return d
    for fmt in ("%a, %d %b %Y %H:%M:%S %Z", "%Y-%m-%d"):
        try:
            return datetime.strptime(d, fmt)
        except Exception:
            continue
    return None

def find_match_for_bet(bet, matches):
    """
    Griežtas sutapimas:
    - ta pati diena (pagal 'YYYY-MM-DD' arba GMT stringą)
    - komandos 1:1 (turi sutapti pavadinimai)
    """
    bet_date = parse_date(str(bet["event"]["date"]))
    team1 = bet["event"]["team_1"]
    team2 = bet["event"]["team_2"]

    for m in matches:
        match_date = parse_date(str(m.get("date")))
        if not match_date:
            continue
        kom1 = m["comand1"]["name"]
        kom2 = m["comand2"]["name"]
        if match_date == bet_date and team1 == kom1 and team2 == kom2:
            return m
    return None

def get_match_result(match):
    """Grąžina (winner, (goals1, goals2)). winner ∈ {komandos pavadinimas, 'draw', None}."""
    t1 = match["comand1"]["name"]
    t2 = match["comand2"]["name"]

    r1 = match["comand1"].get("result", {}) or {}
    r2 = match["comand2"].get("result", {}) or {}

    winner = None
    if r1.get("status") == "won":
        winner = t1
    elif r2.get("status") == "won":
        winner = t2
    elif r1.get("status") == "draw" or r2.get("status") == "draw":
        winner = "draw"

    score = (r1.get("goalsFor"), r2.get("goalsFor"))
    return winner, score

# ---------- Seed (2 bet'ai) ----------
def _print_api_resp(title, resp, data, payload=None):
    print(f"=== {title} ===")
    if payload is not None:
        try:
            import json as _json
            print("Payload:", _json.dumps(payload, indent=2, ensure_ascii=False))
        except Exception:
            print("Payload:", payload)
    print("Status:", getattr(resp, "status_code", "n/a"))
    try:
        import json as _json
        print("Response:", _json.dumps(data, indent=2, ensure_ascii=False))
    except Exception:
        print("Response:", data)
    print()

def _post_bet(payload):
    url = f"{BASE_URL}/bets"
    try:
        resp, data = _post(url, json=payload)
    except Exception as e:
        print(f"❌ Klaida siunčiant POST /bets: {e}")
        return
    _print_api_resp("POST /bets", resp, data, payload)

def seed_two_bets():
    """
    Įrašo 2 bet'us:
      1) choice='winner' (Vilnius FC vs Kaunas United, 2025-10-08)
      2) choice='score'  (Vilnius FC vs Kaunas United, 2025-10-08, 4:2)
    Pastaba: /bets endpointas tikrina ar toks matchas egzistuoja.
    Tad užtikrink, kad 'matches' kolekcijoje yra atitinkami įrašai.
    """
    bet_winner = {
        "userId": SEED_USER_ID,
        "userEmail": SEED_USER_EMAIL,
        "event": {
            "team_1": "Vilnius FC",
            "team_2": "Kaunas United",
            "type": "league",
            "date": "2025-10-08"
        },
        "bet": {
            "choice": "winner",
            "team": "Vilnius FC",
            "odds": 2.5,
            "stake": 50.0
        }
    }

    bet_score = {
        "userId": SEED_USER_ID,
        "userEmail": SEED_USER_EMAIL,
        "event": {
            "team_1": "Vilnius FC",
            "team_2": "Kaunas United",
            "type": "league",
            "date": "2025-10-08"
        },
        "bet": {
            "choice": "score",
            "score": {"team_1": 4, "team_2": 2},
            "odds": 7.36,
            "stake": 16.5
        }
    }

    print("Įrašoma 1/2 (winner)...")
    _post_bet(bet_winner)

    print("Įrašoma 2/2 (score)...")
    _post_bet(bet_score)

    print("Seed'inimas baigtas.\n")

# ---------- Programos įėjimas ----------
def main():
    print("=== PRADŽIA: STATYMŲ SUVEDIMO SCENARIJUS ===")

    # 0) Pasirinktinai: seed'inam 2 bet'us
    if SEED_BETS:
        seed_two_bets()

    today = datetime.now()

    # 1) Pasiimam laukiančius statymus ir visus match'us
    bets = get_pending_bets()
    matches = get_matches()

    # 2) Einam per kiekvieną statymą
    for bet in bets:
        match = find_match_for_bet(bet, matches)
        if not match:
            print(f"⚠️ Nerastos rungtynės statymui {bet.get('_id')} "
                  f"({bet['event']['team_1']} vs {bet['event']['team_2']}, {bet['event']['date']})")
            continue

        match_date = parse_date(str(match.get("date")))
        if not match_date:
            print(f"⚠️ Nepavyko išparsuoti rungtynių datos (bet {bet.get('_id')})")
            continue

        if match_date > today:
            # rungtynės dar nesuvestos – praleidžiam
            continue

        # nustatome realų rezultatą
        winner, score = get_match_result(match)

        # paskaičiuojame statymo baigtį
        status = "lost"
        if bet["bet"]["choice"] == "winner":
            pick = bet["bet"].get("team")
            if pick == winner or (winner == "draw" and pick == "draw"):
                status = "won"
        elif bet["bet"]["choice"] == "score":
            bet_score = bet["bet"].get("score", {}) or {}
            if (bet_score.get("team_1") == score[0] and bet_score.get("team_2") == score[1]):
                status = "won"

        # 3) Atnaujinam statymo statusą
        ok, _ = update_bet_status(bet["_id"], status)
        if ok:
            print(f"✅ Statymas {bet['_id']} → {status}")
        else:
            print(f"❌ Statymo {bet['_id']} statuso atnaujinti nepavyko → {status}")
            continue  # jei statuso nepavyko pakeisti, balansą praleidžiam

        # 4) Atnaujinam vartotojo balansą
        user_id = bet.get("userId")
        user_email = bet.get("userEmail")
        user = get_user_by_id_or_email(user_id, user_email)
        if not user:
            print(f"⚠️ Vartotojas {user_id} / {user_email} nerastas – balansas nepakeistas")
            continue

        try:
            balance = float(user.get("balance", 0))
        except Exception:
            balance = 0.0

        stake = float(bet["bet"]["stake"])
        odds = float(bet["bet"].get("odds", 1))

        if status == "won":
            balance += stake * odds
        else:
            balance -= stake

        ok, _ = update_user_balance(user["_id"], balance)
        if ok:
            print(f"💰 Vartotojo {user.get('email')} balansas → {balance:.2f}")
        else:
            print(f"⚠️ Balanso atnaujinti nepavyko vartotojui {user.get('email')} (palikta nepakeista)")

    print("=== PABAIGA ===")
    return 0

if __name__ == "__main__":
    sys.exit(main())
