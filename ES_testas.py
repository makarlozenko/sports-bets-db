# -*- coding: utf-8 -*-
import requests
import time
import json

BASE = "http://127.0.0.1:5000"


# ================================================================
# HELPERIAI
# ================================================================
def wait():
    time.sleep(0.4)


def pretty(x):
    return json.dumps(x, indent=4, ensure_ascii=False)


def post(path, json=None):
    print(f"\n=== POST {path} ===")
    if json is not None:
        print("Request JSON:")
        print(pretty(json))
    r = requests.post(BASE + path, json=json)
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


# ================================================================
# TESTINIŲ DUOMENŲ STATYMAS
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
        "score": {
            "team_1": 90,
            "team_2": 75
        },
        "odds": 2.0,
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
        "score": {
            "team_1": 90,
            "team_2": 75
        },
        "odds": 2.0,
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

    # Reset ES (ištrina ir sukuria indeksus iš naujo)
    post("/es/reset")
    time.sleep(3)

    # Sync matches iš DB į ES
    post("/es/sync/matches")
    time.sleep(5)

    # Sync bets iš DB į ES
    post("/es/sync/bets")
    time.sleep(5)

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
    get("/search/matches", params={
        "from": "2025-09-01",
        "to":   "2025-11-30"
    })

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

    print("\n--- Daily revenue ---")
    get("/reports/daily-revenue", params={
        "from": "2025-09-01",
        "to":   "2025-12-12"
    })

    print("\n--- Sport popularity ---")
    get("/reports/sport-popularity")

    print("\n✓ Analitiniai endpointai patikrinti.\n")


# ================================================================
# TEST 04: PILNAS DEMO FLOW BŪTENT BETAMS
# ================================================================
def test_bets_reindex_flow():
    print("\n==============================")
    print("TEST 04: BETS FLOW (INIT → CREATE → ANALYTICS → REINDEX → ANALYTICS → CLEANUP)")
    print("==============================")

    # 1. Inicializuojam indeksus (kaip tavo plane)
    print("\n--- 1. ES indeksų inicializacija (/es/init) ---")
    post("/es/init")
    time.sleep(2)

    # 2. Sukuriam testinius statymus
    print("\n--- 2. Sukuriam testinius statymus (/bets) ---")
    created_bet_ids = []

    r1 = post("/bets", json=bet1_data)
    bet1_id = None
    try:
        body1 = r1.json()
        bet1_id = body1.get("_id") or body1.get("id")
    except Exception:
        pass
    if bet1_id:
        created_bet_ids.append(bet1_id)

    time.sleep(4)

    r2 = post("/bets", json=bet2_data)
    bet2_id = None
    try:
        body2 = r2.json()
        bet2_id = body2.get("_id") or body2.get("id")
    except Exception:
        pass
    if bet2_id:
        created_bet_ids.append(bet2_id)

    time.sleep(4)


    # 3. Analitika PRIEŠ reindeksavimą
    print("\n--- 3. Analitika PRIEŠ reindex (/reports/...) ---")
    print("\n[Prieš reindex] Daily revenue:")
    get("/reports/daily-revenue", params={
        "from": "2025-09-01",
        "to":   "2025-12-12"
    })
    print("\n[Prieš reindex] Sport popularity:")
    get("/reports/sport-popularity")

    # 4. Reindeksuojam bets indeksą
    print("\n--- 4. Reindeksavimas (/admin/reindex/bets) ---")
    post("/admin/reindex/bets")
    time.sleep(5)

    # 5. Analitika PO reindeksavimo
    print("\n--- 5. Analitika PO reindex (/reports/...) ---")
    print("\n[Po reindex] Daily revenue:")
    get("/reports/daily-revenue", params={
        "from": "2025-09-01",
        "to":   "2025-12-12"
    })
    print("\n[Po reindex] Sport popularity:")
    get("/reports/sport-popularity")

    # 6. Testinių statymų išvalymas (kad neliktų šiukšlių DB)
    print("\n--- 6. Testinių statymų išvalymas (DELETE /bets/{id}) ---")
    for bet_id in created_bet_ids:
        if bet_id:
            delete(f"/bets/{bet_id}")
            time.sleep(4)

    print("\n✓ Bets reindex demo pilnai įvykdytas.\n")


# ================================================================
# RUN TEST SUITE
# ================================================================
if __name__ == "__main__":
    print("\n=== ES SEARCH / ANALYTICS TESTŲ PALEIDIMAS ===")

    # 1) parodai pilną reset + sync funkcionalumą
    test_reset_and_sync()

    # 2) parodai search (matchai, komandos)
    test_search()

    # 3) parodai analitiką (bendra)
    test_analytics()

    # 4) pagrindinis demo dėstytojui – būtent bets indeksas:
    #    init → sukurti statymus → analitika → reindex → analitika → ištrinti testinius statymus
    test_bets_reindex_flow()

    print("\n=== TESTAVIMAS BAIGTAS SĖKMINGAI ===\n")
