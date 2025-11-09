import gevent.monkey
gevent.monkey.patch_all()

from cassandra.cluster import Cluster
from datetime import datetime, date
import uuid

# Connect to Cassandra
cluster = Cluster(['localhost'])
session = cluster.connect('sportsbook')


def user_exists(user_id):
    existing_users = ["68f27893e6f79eef77a5c165", "3b43df693db1b3fec4f1746b"]
    return user_id in existing_users


def match_exists(match_id):
    existing_matches = ["68e7b61ff2656d90ad339de9"]
    return match_id in existing_matches


# Clear all chat data
def clear_chat_tables():
    session.execute("TRUNCATE chat_messages_by_room;")
    session.execute("TRUNCATE chat_messages_by_user_day;")
    session.execute("TRUNCATE chat_messages_by_user;")
    print("All chat tables cleared.\n")


# Show all chat tables
def show_all_data():
    print("chat_messages_by_room:")
    rows = session.execute("SELECT * FROM chat_messages_by_room;")
    for row in rows:
        print(row)

    print("\nchat_messages_by_user_day:")
    rows = session.execute("SELECT * FROM chat_messages_by_user_day;")
    for row in rows:
        print(row)

    print("\nchat_messages_by_user:")
    rows = session.execute("SELECT * FROM chat_messages_by_user;")
    for row in rows:
        print(row)
    print("")


# Add message with validation
def add_chat_message(match_id, user_id, user_email, message_text):
    if not match_exists(match_id):
        print(f"Match {match_id} not found.")
        return
    if not user_exists(user_id):
        print(f"User {user_id} not found.")
        return

    message_id = uuid.uuid4()
    sent_at = datetime.now()
    day = date.today()
    ttl_seconds = 172800  # 2 days

    #  by match (room)
    session.execute("""
        INSERT INTO chat_messages_by_room (match_id, message_id, user_id, user_email, message, sent_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        USING TTL %s
    """, (match_id, message_id, user_id, user_email, message_text, sent_at, ttl_seconds))

    #  by user and day
    session.execute("""
        INSERT INTO chat_messages_by_user_day (user_id, day, message_id, match_id, message, sent_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        USING TTL %s
    """, (user_id, day, message_id, match_id, message_text, sent_at, ttl_seconds))

    # by user (no day)
    session.execute("""
        INSERT INTO chat_messages_by_user (user_id, message_id, match_id, message, sent_at)
        VALUES (%s, %s, %s, %s, %s)
        USING TTL %s
    """, (user_id, message_id, match_id, message_text, sent_at, ttl_seconds))

    print(f"Message added: {message_text}")


# Main test script
if __name__ == "__main__":
    match_id = "68e7b61ff2656d90ad339de9"
    user1_id = "68f27893e6f79eef77a5c165"
    user2_id = "3b43df693db1b3fec4f1746b"

    user1_email = "arina.ti@outlook.com"
    user2_email = "deividas.kazlauskas8@outlook.com"

    print("1) Clearing existing chat data...")
    clear_chat_tables()

    print("2) Showing that tables are empty:")
    show_all_data()

    print("3) Inserting new messages:")
    add_chat_message(match_id, user1_id, user1_email, "Vilnius Wolves are dominating tonight!")
    add_chat_message(match_id, user2_id, user2_email, "Panevezys Titans still have a chance to win.")
    add_chat_message(match_id, user1_id, user1_email, "That three-pointer was perfect.")
    add_chat_message(match_id, user2_id, user2_email, "Defense needs improvement.")

    print("\n4) Showing data in all tables after insertion:")
    show_all_data()

    print("5) Trying to add message from a non-existent user:")
    add_chat_message(match_id, "fake_user_001", "fake@example.com", "This should not be saved.")

    print("\n6) Final data in all tables:")
    show_all_data()

    cluster.shutdown()
