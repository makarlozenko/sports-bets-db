import threading
import requests
import time
import uuid

BASE_URL = "http://127.0.0.1:5050"  # поменяй, если у тебя другой порт

# Данные ставки
payload = {
    "userId": "d1449f76f78f46d2ac09d832",  # вставь свой существующий userId
    "userEmail": "aurimas.mikalauskas13@gmail.com",
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
        "stake": 10.0
    },
    # requestId нужен для идемпотентности
    "requestId": str(uuid.uuid4())
}

def send_bet(thread_name):
    print(f"[{thread_name}] sending request...")
    t0 = time.time()
    resp = requests.post(f"{BASE_URL}/bets", json=payload, timeout=15)
    dt = time.time() - t0
    print(f"[{thread_name}] Response ({resp.status_code}) after {dt:.2f}s: {resp.text}\n")

# Запускаем два запроса почти одновременно
t1 = threading.Thread(target=send_bet, args=("Thread-1",))
t2 = threading.Thread(target=send_bet, args=("Thread-2",))

t1.start()
time.sleep(0.1)  # минимальная задержка (чтобы столкнулись)
t2.start()

t1.join()
t2.join()