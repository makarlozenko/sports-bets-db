import gevent.monkey
gevent.monkey.patch_all()

from cassandra.cluster import Cluster
from datetime import datetime, date
import uuid

# -----------------------------------
#  DEMO: Cassandra Chat Functionality
# -----------------------------------

def connect_to_cassandra():
    """Try to connect to Cassandra container."""
    print("🔌 Connecting to Cassandra container...")
    try:
        cluster = Cluster(['localhost'])
        session = cluster.connect('sportsbook')
        print("Connected successfully to keyspace 'sportsbook'\n")
        return cluster, session
    except Exception as e:
        print(f"Connection failed: {e}")
        exit(1)


def user_exists(session, user_id):
    result = session.execute("SELECT user_id FROM users WHERE user_id = %s;", [user_id])
    return result.one() is not None


def match_exists(session, match_id):
    result = session.execute("SELECT match_id FROM matches WHERE match_id = %s;", [match_id])
    return result.one() is not None


def add_chat_message(session, match_id, user_id, user_email, message_text):
    """Add a chat message if both user and match exist."""
    print(f"Trying to add message from {user_email} (user_id={user_id}) to match {match_id}...")
    if not match_exists(session, match_id):
        print(f"Match {match_id} not found.\n")
        return
    if not user_exists(session, user_id):
        print(f"User {user_id} not found.\n")
        return

    message_id = uuid.uuid4()
    sent_at = datetime.now()
    day = date.today()

    session.execute("""
        INSERT INTO chat_messages_by_room (match_id, message_id, user_id, user_email, message, sent_at)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (match_id, message_id, user_id, user_email, message_text, sent_at))

    session.execute("""
        INSERT INTO chat_messages_by_user_day (user_id, day, message_id, match_id, message, sent_at)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (user_id, day, message_id, match_id, message_text, sent_at))

    print(f"Message added successfully (TTL = 2 days)\n")


def show_all_chat_messages(session):
    """Display all chat messages currently stored."""
    print("Current chat_messages_by_room content:")
    rows = session.execute("SELECT match_id, user_email, message, sent_at, TTL(message) AS ttl FROM chat_messages_by_room;")
    found = False
    for r in rows:
        found = True
        print(f"  Match {r.match_id} | {r.user_email} | '{r.message}' | sent at {r.sent_at} | TTL left: {r.ttl}s")
    if not found:
        print("  (No chat messages found.)")
    print()


def run_demo():
    """Run the entire demonstration."""
    cluster, session = connect_to_cassandra()

    print("=== Step 1: Check environment ===")
    print("Keyspace: sportsbook")
    print("Tables: chat_messages_by_room, chat_messages_by_user_day, users, matches\n")

    # Known existing IDs (from your DB)
    match_id = "68e7b61ff2656d90ad339de9"   # Vilnius Wolves vs Panevezys Titans
    user_id = "68f27893e6f79eef77a5c165"    # Arina
    user_email = "arina.ti@outlook.com"

    # Step 2: Try adding valid message
    print("=== Step 2: Adding a valid chat message ===")
    add_chat_message(session, match_id, user_id, user_email, "Vilnius Wolves are playing great today! 🏀")

    # Step 3: Try adding message from non-existing user
    print("=== Step 3: Adding message from non-existing user ===")
    add_chat_message(session, match_id, "fake_user_000", "fake@mail.com", "This should fail ")

    # Step 4: Display current messages
    print("=== Step 4: Show current chat table content ===")
    show_all_chat_messages(session)

    # Step 5: Simulate another user
    print("=== Step 5: Adding second user's message ===")
    add_chat_message(session, match_id, "3b43df693db1b3fec4f1746b", "deividas.kazlauskas8@outlook.com", "Panevezys Titans will bounce back soon!")

    print("=== Step 6: Final chat snapshot ===")
    show_all_chat_messages(session)

    cluster.shutdown()
    print("Cassandra connection closed.")


# -----------------------------
# Main entry point
# -----------------------------
if __name__ == "__main__":
    run_demo()
