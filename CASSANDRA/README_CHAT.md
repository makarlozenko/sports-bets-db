# 💬 Cassandra Chat Functionality (Sportsbook Project)

This project implements **chat functionality** on top of the existing `sportsbook` Cassandra database.  
It allows users to send messages related to sports matches, stores them in two separate tables,  
and automatically expires old messages after 2 days (using TTL).

---

## 🚀 Features

- **Two-table message storage design:**
  - `chat_messages_by_room` → messages grouped by match (`match_id`).
  - `chat_messages_by_user_day` → messages grouped by user and date (`user_id`, `day`).

- **Automatic synchronization:**  
  Every message written to the match chat is also written to the user/day chat.

- **Automatic message expiration (TTL):**  
  All messages are automatically deleted after **2 days (172,800 seconds)**.

- **Safe validation:**  
  Before inserting, the system checks whether both the `user_id` and `match_id` exist  
  in the corresponding tables (`users`, `matches`).

- **No ALLOW FILTERING:**  
  All queries are based on primary keys for efficient reads.

- **Clean test/demo files:**
  - `chat_service.py` – core chat logic (insert, read, validation).
  - `chat_demo.py` – visual demo with TTL, errors, and live data check.
  - `chat_schema.cql` – table structure with TTL rules.

---

## 🧱 Database Schema (excerpt)

```sql
CREATE TABLE IF NOT EXISTS chat_messages_by_room (
    match_id text,
    message_id uuid,
    user_id text,
    user_email text,
    message text,
    sent_at timestamp,
    PRIMARY KEY (match_id, message_id)
) WITH CLUSTERING ORDER BY (message_id ASC)
  AND default_time_to_live = 172800; -- 2 days

CREATE TABLE IF NOT EXISTS chat_messages_by_user_day (
    user_id text,
    day date,
    message_id uuid,
    match_id text,
    message text,
    sent_at timestamp,
    PRIMARY KEY ((user_id, day), message_id)
) WITH CLUSTERING ORDER BY (message_id ASC)
  AND default_time_to_live = 172800; -- 2 days
```

---

## 🧩 How It Works

1. **Add a message:**
   - The system checks if the user and match exist.
   - Message is inserted into both chat tables.
   - Each record automatically expires after 2 days.

2. **Read messages:**
   - From `chat_messages_by_room`: get all messages in a match.
   - From `chat_messages_by_user_day`: get all user’s messages for today.

3. **Automatic deletion:**
   - Cassandra’s TTL cleans expired messages without manual intervention.

---

## 🧪 Demo Script (`chat_demo.py`)

Run a full demonstration in terminal:

```bash
python chat_demo.py
```

This will:
1. Check Cassandra connection and keyspace.
2. Insert a valid message from a real user.
3. Attempt to insert a message from a non-existent user (shows error).
4. Display current messages with TTL remaining.
5. Add another valid message.
6. Display final chat state and close connection.

---

### 🖥️ Example Output

```
🔌 Connecting to Cassandra container...
✅ Connected successfully to keyspace 'sportsbook'

=== Step 2: Adding a valid chat message ===
✅ Message added successfully (TTL = 2 days)

=== Step 3: Adding message from non-existing user ===
❌ User fake_user_000 not found.

=== Step 4: Show current chat table content ===
📜 Current chat_messages_by_room content:
  Match 68e7b61ff2656d90ad339de9 | arina.ti@outlook.com | 'Vilnius Wolves are playing great today!' | TTL left: 172799s
```

---

## 🧰 Setup Instructions

1. **Run Cassandra container:**
   ```bash
   docker start cassandra
   ```

2. **Apply schema:**
   ```bash
   docker cp chat_schema.cql cassandra:/chat_schema.cql
   docker exec -it cassandra cqlsh -e "SOURCE '/chat_schema.cql';"
   ```

3. **Install dependencies:**
   ```bash
   pip install scylla-driver gevent greenlet
   ```

4. **Run the service or demo:**
   ```bash
   python chat_service.py
   # or
   python chat_demo.py
   ```

---

## ✅ Project Goals Achieved

| Requirement | Status |
|--------------|----------|
| Messages written to two tables | ✅ Done |
| Reading by match and by user/day | ✅ Done |
| Automatic expiration (TTL) | ✅ Done |
| No ALLOW FILTERING | ✅ Done |
| Validation of user/match | ✅ Done |
| Testing and demonstration | ✅ Done |

---

## 🏁 Author
**Makar**  
Cassandra Chat Functionality – Sports Bets DB Project (University Assignment)
