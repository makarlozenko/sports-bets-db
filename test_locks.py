import threading
import requests
import time
import uuid

BASE_URL = "http://127.0.0.1:5000"

payload = {
  "userId": "68f27893e6f79eef77a5c165",
  "userEmail": "arina.ti@outlook.com",
  "event": {
    "team_1": "Vilnius Wolves",
    "team_2": "Kaunas Green",
    "type": "league",
    "date": "2025-09-01"

  },
  "bet": {
    "choice": "winner",
    "team": "Vilnius Wolves",
    "stake": 20.00,
    "createdAt": "2025-07-01"

  },
  "requestId": str(uuid.uuid4())
}

def send_bet(thread_name):
    print(f"[{thread_name}] sending request...")
    t0 = time.time()
    resp = requests.post(f"{BASE_URL}/bets", json=payload, timeout=15)
    dt = time.time() - t0
    print(f"[{thread_name}] Response ({resp.status_code}) after {dt:.2f}s: {resp.text}\n")

t1 = threading.Thread(target=send_bet, args=("Thread-1",))
t2 = threading.Thread(target=send_bet, args=("Thread-2",))

t1.start()
time.sleep(0.1)
t2.start()

t1.join()
t2.join()

print("=== Testing idempotency ===")
resp1 = requests.post(f"{BASE_URL}/bets", json=payload)
resp2 = requests.post(f"{BASE_URL}/bets", json=payload)
print("First:", resp1.status_code, resp1.text)
print("Second:", resp2.status_code, resp2.text)