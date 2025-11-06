import gevent.monkey
gevent.monkey.patch_all()

from cassandra.cluster import Cluster
from datetime import datetime, date
import uuid

# -----------------------------------
# Cassandra Chat Service
# -----------------------------------

def connect_to_cassandra():
    """Connect to the local Cassandra cluster and return the session."""
    cluster = Cluster(['localhost'])
    session = cluster.connect('sportsbook')
    return cluster, session


def user_exists(session, user_id):
    """Check if the user exists in the 'users' table."""
    query = "SELECT user_id FROM users WHERE user_id = %s;"
    result = session.execute(query, [user_id])
    return result.one() is not None


def match_exists(session, match_id):
    """Check if the match exists in the 'matches' table."""
    query = "SELECT match_id FROM matches WHERE match_id = %s;"
    result = session.execute(query, [match_id])
    return result.one() is not None


def add_chat_message(session, match_id, user_id, user_email, message_text):
    """Insert a new chat message into both chat tables."""
    if not match_exists(session, match_id):
        print(f"Match {match_id} not found.")
        return
    if not user_exists(session, user_id):
        print(f"User {user_id} not found.")
        return

    message_id = uuid.uuid4()
    sent_at = datetime.now()
    day = date.today()

    # Insert into chat by match (chat room)
    session.execute("""
        INSERT INTO chat_messages_by_room (match_id, message_id, user_id, user_email, message, sent_at)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (match_id, message_id, user_id, user_email, message_text, sent_at))

    # Insert into chat by user/day (user history)
    session.execute("""
        INSERT INTO chat_messages_by_user_day (user_id, day, message_id, match_id, message, sent_at)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (user_id, day, message_id, match_id, message_text, sent_at))

    print(f"Message successfully added for match {match_id} (user: {user_email})")


def show_messages_by_match(session, match_id):
    """Display all messages for a specific match (chat room)."""
    rows = session.execute(
        "SELECT * FROM chat_messages_by_room WHERE match_id = %s", [match_id]
    )
    print(f"\nChat for match {match_id}:")
    found = False
    for r in rows:
        found = True
        print(f"  [{r.sent_at:%Y-%m-%d %H:%M:%S}] {r.user_email}: {r.message}")
    if not found:
        print("  (No messages yet.)")


def show_messages_by_user(session, user_id):
    """Display all today's messages sent by a specific user."""
    rows = session.execute("""
        SELECT * FROM chat_messages_by_user_day
        WHERE user_id = %s AND day = toDate(now());
    """, [user_id])
    print(f"\nMessages by user {user_id} (today):")
    found = False
    for r in rows:
        found = True
        print(f"  [{r.sent_at:%Y-%m-%d %H:%M:%S}] Match {r.match_id}: {r.message}")
    if not found:
        print("  (No messages yet.)")


# -----------------------------------
# Test run
# -----------------------------------

if __name__ == "__main__":
    cluster, session = connect_to_cassandra()

    # Example: real data from your DB
    match_id = "68e7b61ff2656d90ad339de9"   # Vilnius Wolves vs Panevezys Titans
    user_id = "68f27893e6f79eef77a5c165"    # Arina
    user_email = "arina.ti@outlook.com"
    message_text = "Vilnius Wolves are on fire tonight! 🔥"

    print("\n--- Adding chat message ---")
    add_chat_message(session, match_id, user_id, user_email, message_text)

    print("\n--- Fetching chat messages by match ---")
    show_messages_by_match(session, match_id)

    print("\n--- Fetching chat messages by user ---")
    show_messages_by_user(session, user_id)

    cluster.shutdown()
    print("\nCassandra connection closed.")
