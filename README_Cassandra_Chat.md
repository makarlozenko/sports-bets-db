# Cassandra Chat Integration with MongoDB

This project extends an existing sports betting platform with a chat system that uses Cassandra for storing messages and MongoDB for validation of users and matches.

---

## 1. System Overview

**MongoDB**  
Used to store users, matches, and other application data.  
Collections:
- `User`
- `Matches`

**Cassandra**  
Used for chat message storage.  
Keyspace: `sportsbook`  
Tables:
- `chat_messages_by_room`
- `chat_messages_by_user_day`

Messages are automatically removed after 2 days via TTL (time-to-live).

---

## 2. Chat Table Structures

```sql
CREATE TABLE sportsbook.chat_messages_by_room (
    match_id text,
    message_id uuid,
    message text,
    sent_at timestamp,
    user_email text,
    user_id text,
    PRIMARY KEY (match_id, message_id)
) WITH CLUSTERING ORDER BY (message_id ASC)
   AND default_time_to_live = 172800;  -- 2 days

CREATE TABLE sportsbook.chat_messages_by_user_day (
    user_id text,
    day date,
    message_id uuid,
    match_id text,
    message text,
    sent_at timestamp,
    PRIMARY KEY (user_id, day, message_id)
) WITH CLUSTERING ORDER BY (message_id ASC)
   AND default_time_to_live = 172800;  -- 2 days
```

---

## 3. Flask Chat API (`chat.py`)

This file provides CRUD-like endpoints for chat messages with validation through MongoDB.

### Endpoints

#### `POST /chat/messages`
Creates a new message.

**Request body:**
```json
{
  "matchId": "68e7b61ff2656d90ad339de9",
  "userId": "68f27893e6f79eef77a5c165",
  "userEmail": "arina.ti@outlook.com",
  "message": "Vilnius Wolves are unstoppable tonight!"
}
```

**Behavior:**
- Validates that both user and match exist in MongoDB.
- Writes message to both Cassandra tables.
- Each message expires automatically after 2 days (TTL 172800 seconds).

#### `GET /chat/match/<match_id>`
Retrieves all messages for a given match.

#### `GET /chat/user/<user_id>`
Retrieves all messages sent by a given user on the current day.

#### `DELETE /chat/clear`
Clears all chat messages (for testing).

#### `GET /chat/debug/mongo`
Shows counts of users and matches in MongoDB.

#### `GET /chat/health`
Returns chat system status and TTL info.

---

## 4. Testing Script (`chat_test_script.py`)

This standalone script directly interacts with Cassandra to validate functionality.

### Behavior
1. Connects to Cassandra.
2. Clears all chat tables.
3. Verifies they are empty.
4. Inserts several valid messages.
5. Displays all data in both tables.
6. Attempts to insert an invalid message from a non-existent user.
7. Displays final table contents.

### Example Output
```
1) Clearing existing chat data...
All chat tables cleared.

2) Showing that tables are empty:
chat_messages_by_room:
chat_messages_by_user_day:

3) Inserting new messages:
Message added: Vilnius Wolves are dominating tonight!
Message added: Panevezys Titans still have a chance to win.
Message added: That three-pointer was perfect.

4) Showing data in both tables after insertion:
Rows listed for both tables...

5) Trying to add message from a non-existent user:
User fake_user_001 not found.
```

---

## 5. How to Run

1. Start Cassandra:
   ```bash
   docker start cassandra
   ```

2. Start Flask application:
   ```bash
   python main.py
   ```

3. (Optional) Run standalone chat test:
   ```bash
   python chat_test_script.py
   ```

---

## 6. Integration Notes

- `user_exists()` and `match_exists()` use MongoDB `ObjectId` for validation.  
- Messages are immutable: direct updates are not supported (`PATCH` returns a warning).  
- Expiration handled automatically by Cassandra TTL.  
- API tested with Postman.

---

## 7. Environment

- **Python**: 3.12+
- **Flask**: 3.x
- **Cassandra Driver**: `scylla-driver`
- **MongoDB Driver**: `pymongo`
- **Database Names**
  - Cassandra keyspace: `sportsbook`
  - MongoDB database: `SportBET`

---
