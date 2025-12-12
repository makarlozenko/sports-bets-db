# -*- coding: utf-8 -*-
import requests
import time
import json

BASE = "http://127.0.0.1:5000"

# ================================================================
# HELPERIAI
# ================================================================
def wait(sec=0.6):
    time.sleep(sec)

def pretty(x):
    return json.dumps(x, indent=4, ensure_ascii=False)

def post(path, json_body=None):
    print(f"\n=== POST {path} ===")
    if json_body is not None:
        print("Request JSON:")
        print(pretty(json_body))
    r = requests.post(BASE + path, json=json_body)
    print("Response:", r.status_code)
    try:
        print(pretty(r.json()))
    except Exception:
        print(r.text)
    return r

def get(path, params=None):
    print(f"\n=== GET {path} ===")
    if params:
        print("Params:", params)
    r = requests.get(BASE + path, params=params)
    print("Response:", r.status_code)
    try:
        print(pretty(r.json()))
    except Exception:
        print(r.text)
    return r

def delete(path):
    print(f"\n=== DELETE {path} ===")
    r = requests.delete(BASE + path)
    print("Response:", r.status_code)
    try:
        print(pretty(r.json()))
    except Exception:
        print(r.text)
    return r

def extract_bet_id(resp):
    """
    Tavo /bets create grąžina {"message": "...", "bet": {...}}
    _id būna bet objekte: body["bet"]["_id"]
    """
    try:
        body = resp.json()
    except Exception:
        return None
    bet_obj = body.get("bet") or {}
    return bet_obj.get("_id")

# ================================================================
# TESTINIAI BETAI (PASTABA: odds backend’e imami iš Matches, ne iš bet)
# ================================================================
bet1_data = {
    "userId": "20ba1f0e3b20a2c5dcce32d6",
    "userEmail": "rytis.jankauskas13@gmail.com",
    "event": {
        "team_1": "Vilnius FC",
        "team_2": "Panevezys Town",
        "type": "league",
        "date": "2025-08-29"
    },
    "bet": {
        "choice": "score",
        "score": {"team_1": 90, "team_2": 75},
        "stake": 10.0
    }
}

bet2_data = {
    "userId": "20ba1f0e3b20a2c5dcce32d6",
    "userEmail": "rytis.jankauskas13@gmail.com",
    "event": {
        "team_1": "Vilnius FC",
        "team_2": "Kaunas United",
        "type": "league",
        "date": "2025-08-15"
    },
    "bet": {
        "choice": "score",
        "score": {"team_1": 90, "team_2": 75},
        "stake": 10.0
    }
}

# ================================================================
# TEST 01: ES RESET + SYNC
# ================================================================
def test_reset_and_sync():
    print("\n==============================")
    print("TEST 01: RESET + SYNC MATCHES/BETS")
    print("==============================")

    post("/es/reset")
    wait(3)

    post("/es/sync/matches")
    wait(4)

    post("/es/sync/bets")
    wait(4)

    print("\n✓ ES reset + pilna sinchronizacija atlikta.\n")

# ================================================================
# TEST 02: SEARCH (MATCHES / TEAMS)
# ================================================================
def test_search():
    print("\n==============================")
    print("TEST 02: SEARCH ENDPOINTAI")
    print("==============================")

    print("\n--- Search pagal komandą 'Vilnius' ---")
    get("/search/matches", params={"team": "Vilnius"})

    print("\n--- Search pagal sportą ---")
    get("/search/matches", params={"sport": "football"})

    print("\n--- Search pagal datų intervalą ---")
    get("/search/matches", params={"from": "2025-09-01", "to": "2025-11-30"})

    print("\n--- Autocomplete teams ---")
    get("/search/teams", params={"q": "Vi"})

    print("\n✓ Visi search endpointai patikrinti.\n")

# ================================================================
# TEST 03: ANALYTICS (BETS)
# ================================================================
def test_analytics():
    print("\n==============================")
    print("TEST 03: ANALYTICS ENDPOINTAI")
    print("==============================")

    # Daily revenue pas tave dabar yra pagal matchDate, todėl duodam intervalą,
    # kuris apima ir 2025-08-15, ir 2025-08-29, ir pan.
    print("\n--- Daily revenue (pagal matchDate) ---")
    get("/reports/daily-revenue", params={"from": "2025-08-01", "to": "2025-12-12"})

    print("\n--- Sport popularity ---")
    get("/reports/sport-popularity")

    print("\n✓ Analitiniai endpointai patikrinti.\n")

# ================================================================
# TEST 04: PILNAS DEMO FLOW (BETS)
# ================================================================
def test_bets_reindex_flow():
    print("\n==============================")
    print("TEST 04: BETS FLOW (INIT → CREATE → ANALYTICS → REINDEX → ANALYTICS → CLEANUP)")
    print("==============================")

    # 1. Inicializuojam indeksus
    print("\n--- 1. ES indeksų inicializacija (/es/init) ---")
    post("/es/init")
    wait(2)

    # 2. Sukuriam testinius statymus
    print("\n--- 2. Sukuriam testinius statymus (/bets) ---")
    created_bet_ids = []

    r1 = post("/bets", json_body=bet1_data)
    bet1_id = extract_bet_id(r1)
    if bet1_id:
        created_bet_ids.append(bet1_id)
    else:
        print("(!) bet1 nebuvo sukurtas (gal duplicate / insufficient balance).")

    wait(2)

    r2 = post("/bets", json_body=bet2_data)
    bet2_id = extract_bet_id(r2)
    if bet2_id:
        created_bet_ids.append(bet2_id)
    else:
        print("(!) bet2 nebuvo sukurtas (gal duplicate / insufficient balance).")

    # palaukiam, kad ES spėtų susiindeksuoti (create_bet daro es.index)
    wait(3)

    # 3. Analitika PRIEŠ reindeksavimą
    print("\n--- 3. Analitika PRIEŠ reindex (/reports/...) ---")
    print("\n[Prieš reindex] Daily revenue:")
    get("/reports/daily-revenue", params={"from": "2025-08-01", "to": "2025-12-12"})
    print("\n[Prieš reindex] Sport popularity:")
    get("/reports/sport-popularity")

    # 4. Reindeksuojam bets indeksą
    print("\n--- 4. Reindeksavimas (/admin/reindex/bets) ---")
    post("/admin/reindex/bets")
    wait(4)

    # 5. Analitika PO reindeksavimo
    print("\n--- 5. Analitika PO reindex (/reports/...) ---")
    print("\n[Po reindex] Daily revenue:")
    get("/reports/daily-revenue", params={"from": "2025-08-01", "to": "2025-12-12"})
    print("\n[Po reindex] Sport popularity:")
    get("/reports/sport-popularity")

    # 6. Testinių statymų išvalymas
    print("\n--- 6. Testinių statymų išvalymas (DELETE /bets/{id}) ---")
    if not created_bet_ids:
        print("(!) Nėra ką trinti (nei vienas testinis betas nesusikūrė).")
    for bet_id in created_bet_ids:
        delete(f"/bets/{bet_id}")
        wait(1.5)

    print("\n✓ Bets reindex demo pilnai įvykdytas.\n")

# ================================================================
# RUN TEST SUITE
# ================================================================
if __name__ == "__main__":
    print("\n=== ES SEARCH / ANALYTICS TESTŲ PALEIDIMAS ===")

    # 1) reset + sync (parodo kad ES pilnai užsipildo iš DB)
    test_reset_and_sync()

    # 2) search endpointai
    test_search()

    # 3) analitika (bendras vaizdas)
    test_analytics()

    # 4) demo flow: init → create → analytics → reindex → analytics → cleanup
    test_bets_reindex_flow()

    print("\n=== TESTAVIMAS BAIGTAS ===\n")
