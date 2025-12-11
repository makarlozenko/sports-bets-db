import requests
import time
import json

BASE = "http://127.0.0.1:5000"

def wait():
    time.sleep(0.4)

def pretty(x):
    return json.dumps(x, indent=4, ensure_ascii=False)

def post(path, json=None):
    print(f"\n=== POST {path} ===")
    if json:
        print("Request JSON:")
        print(pretty(json))
    r = requests.post(BASE + path, json=json)
    print("Response:", r.status_code)
    try: print(pretty(r.json()))
    except: print(r.text)
    return r

def get(path, params=None):
    print(f"\n=== GET {path} ===")
    if params:
        print("Params:", params)
    r = requests.get(BASE + path, params=params)
    print("Response:", r.status_code)
    try: print(pretty(r.json()))
    except: print(r.text)
    return r


# =================================================================
# TEST 01: RESET + SYNC
# =================================================================
def test_reset_and_sync():
    print("\n==============================")
    print("TEST 01: RESET + SYNC MATCHES/BETS")
    print("==============================")

    # Reset ES
    post("/es/reset")
    wait()

    # Sync matches
    post("/es/sync/matches")
    wait()

    # Sync bets
    post("/es/sync/bets")
    wait()

    print("\n✓ ES reset + pilna sinchronizacija atlikta.\n")


# =================================================================
# TEST 02: SEARCH METHODS
# =================================================================
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
        "from": "2025-01-01",
        "to":   "2025-12-31"
    })

    print("\n--- Autocomplete teams ---")
    get("/search/teams", params={"q": "Vi"})

    print("\n✓ Visi search endpointai patikrinti.\n")


# =================================================================
# TEST 03: ANALYTICS
# =================================================================
def test_analytics():
    print("\n==============================")
    print("TEST 03: ANALYTICS ENDPOINTAI")
    print("==============================")

    print("\n--- Daily revenue ---")
    get("/reports/daily-revenue")

    print("\n--- Sport popularity ---")
    get("/reports/sport-popularity")

    print("\n✓ Analitiniai endpointai veikia.\n")


# =================================================================
# RUN TEST SUITE
# =================================================================
if __name__ == "__main__":
    print("\n=== ES SEARCH / ANALYTICS TESTŲ PALEIDIMAS ===")

    test_reset_and_sync()
    test_search()
    test_analytics()

    print("\n=== TESTAVIMAS BAIGTAS SĖKMINGAI ===\n")
