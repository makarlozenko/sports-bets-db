# Sports Bets Chat System (MongoDB + Cassandra)

This project implements a real-time chat feature for the Sports Bets database.  
The chat system combines MongoDB (for user and match validation) with Cassandra (for scalable message storage).  
It supports multiple retrieval modes and includes TTL-based automatic cleanup.

---

## 1. Overview

The chat system allows users to:
- Post messages linked to a specific sports match.
- Retrieve messages by match or by user.
- Automatically expire messages after 2 days (TTL = 172800 seconds).
- Access historical messages efficiently without using `ALLOW FILTERING`.

The backend is written in **Python (Flask)** and uses:
- **MongoDB** for persistent entities (`Matches`, `Users`).
- **Apache Cassandra** for chat messages storage.

---

## 2. Prerequisites

Before running, ensure you have:

- **Python 3.10+**
- **MongoDB Atlas** or local MongoDB running with collections:
  - `Matches`
  - `User`
- **Apache Cassandra** running locally or via Docker (recommended).

Example Docker command:
```bash
docker run --name cassandra -p 9042:9042 -d cassandra:latest
```

---

## 3. Cassandra Schema

File: `CASSANDRA/chat_schema.cql`

```sql
USE sportsbook;

CREATE TABLE IF NOT EXISTS chat_messages_by_room (
    match_id text,
    message_id uuid,
    user_id text,
    user_email text,
    message text,
    sent_at timestamp,
    PRIMARY KEY (match_id, message_id)
) WITH CLUSTERING ORDER BY (message_id ASC)
  AND default_time_to_live = 172800;

CREATE TABLE IF NOT EXISTS chat_messages_by_user_day (
    user_id text,
    day date,
    message_id uuid,
    match_id text,
    message text,
    sent_at timestamp,
    PRIMARY KEY ((user_id, day), message_id)
) WITH CLUSTERING ORDER BY (message_id ASC)
  AND default_time_to_live = 172800;

CREATE TABLE IF NOT EXISTS chat_messages_by_user (
    user_id text,
    message_id uuid,
    match_id text,
    message text,
    sent_at timestamp,
    PRIMARY KEY (user_id, message_id)
) WITH CLUSTERING ORDER BY (message_id ASC)
  AND default_time_to_live = 172800;
```

---

## 4. Loading the Schema

If Cassandra is running in Docker:

```bash
docker cp chat_schema.cql cassandra:/chat_schema.cql
docker exec -it cassandra cqlsh -f /chat_schema.cql
```

Or directly from your terminal:

```bash
docker exec -i cassandra cqlsh < C:\path\to\chat_schema.cql
```

Verify that the tables were created:

```bash
docker exec -it cassandra cqlsh
USE sportsbook;
DESCRIBE TABLES;
```

---

## 5. Flask Chat Endpoints

The main chat logic is defined in `chat.py`.

### Endpoints Summary

| Method | Endpoint | Description |
|--------|-----------|-------------|
| `POST` | `/chat/messages` | Add a new chat message (validated via MongoDB) |
| `GET` | `/chat/match/<match_id>` | Get messages by match ID |
| `GET` | `/chat/user/<user_id>` | Get all messages by user (recent days) |
| `GET` | `/chat/user/<user_id>/day/<yyyy-mm-dd>` | Get messages for a specific user and day (no ALLOW FILTERING) |
| `DELETE` | `/chat/clear` | Delete all messages manually |
| `GET` | `/chat/health` | Health check endpoint |
| `GET` | `/chat/debug/mongo` | MongoDB stats (users & matches count) |

TTL ensures all messages expire automatically after 48 hours.
For `POST`:
Request body

```json
{
  "matchId": "68e7b61ff2656d90ad339de9",
  "userId": "68f27893e6f79eef77a5c165",
  "userEmail": "arina.ti@outlook.com",
  "message": "Vilnius Wolves are unstoppable tonight!"
}
```
---

## 6. Cassandra Test Script

File: `chat_script.py`  
This standalone Python script verifies chat functionality:
1. Clears existing chat data.
2. Shows that all tables are empty.
3. Inserts test messages.
4. Displays all tables’ contents.
5. Attempts to insert a message from a non-existent user.

Run:
```bash
python chat_script.py
```

Example output:
```
1) Clearing existing chat data...
All chat tables cleared.

2) Showing that tables are empty:
chat_messages_by_room:
chat_messages_by_user_day:
chat_messages_by_user:

3) Inserting new messages:
Message added: Vilnius Wolves are dominating tonight!
Message added: Panevezys Titans still have a chance to win.

4) Showing data in all tables after insertion:
(chat rows printed)

5) Trying to add message from a non-existent user:
User fake_user_001 not found.

6) Final data in all tables:
(chat rows printed)
```

---

## 7. Integration Notes

- All Cassandra writes occur **in parallel** into three tables.
- MongoDB is only used for existence validation (`Matches`, `User`).
- Each Cassandra record includes:
  - `message_id` (UUID)
  - `match_id`
  - `user_id`
  - `user_email`
  - `message`
  - `sent_at` (timestamp)
- Expiration is fully automated by Cassandra’s `TTL`.

---

## 8. Performance and Best Practices

- Avoid using `ALLOW FILTERING` — all read patterns are covered by primary keys.
- Read and write throughput scales linearly with Cassandra cluster size.
- Use the `/chat/user/<user_id>/day/<date>` endpoint for efficient user-based reads.

---

