from flask import request, jsonify
from cassandra.cluster import Cluster
from datetime import datetime, date
import uuid
from bson import ObjectId


def register_chat_routes(app, db):
    MATCHES = db.Matches   # collection
    USERS = db.User

    # Cassandra connection
    cluster = Cluster(['localhost'])
    session = cluster.connect('sportsbook')

    # Mongo validation helpers
    def user_exists(user_id):
        try:
            oid = ObjectId(user_id)
        except Exception:
            return False
        return USERS.find_one({"_id": oid}) is not None

    def match_exists(match_id):
        try:
            oid = ObjectId(match_id)
        except Exception:
            return False
        return MATCHES.find_one({"_id": oid}) is not None

    # CREATE
    @app.post("/chat/messages")
    def create_message():
        data = request.get_json(silent=True) or {}
        match_id = data.get("matchId")
        user_id = data.get("userId")
        user_email = data.get("userEmail")
        message_text = data.get("message")

        if not all([match_id, user_id, user_email, message_text]):
            return jsonify({"error": "matchId, userId, userEmail, and message are required"}), 400

        # Check user and match existence in Mongo
        if not match_exists(match_id):
            return jsonify({"error": f"Match {match_id} not found in Mongo"}), 404
        if not user_exists(user_id):
            return jsonify({"error": f"User {user_id} not found in Mongo"}), 404

        message_id = uuid.uuid4()
        sent_at = datetime.now()
        day = date.today()
        ttl_seconds = 172800  # 2 days

        # 1) by room
        session.execute("""
            INSERT INTO chat_messages_by_room (match_id, message_id, user_id, user_email, message, sent_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            USING TTL %s
        """, (match_id, message_id, user_id, user_email, message_text, sent_at, ttl_seconds))

        # 2) by user and day
        session.execute("""
            INSERT INTO chat_messages_by_user_day (user_id, day, message_id, match_id, message, sent_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            USING TTL %s
        """, (user_id, day, message_id, match_id, message_text, sent_at, ttl_seconds))

        session.execute("""
            INSERT INTO chat_messages_by_user (user_id, message_id, match_id, message, sent_at)
            VALUES (%s, %s, %s, %s, %s)
            USING TTL %s
        """, (user_id, message_id, match_id, message_text, sent_at, ttl_seconds))

        return jsonify({
            "message": "Message created",
            "matchId": match_id,
            "userId": user_id,
            "text": message_text
        }), 201

    @app.get("/chat/debug/mongo")
    def debug_mongo():
        return {
            "users_count": USERS.count_documents({}),
            "matches_count": MATCHES.count_documents({})
        }

    # READ: messages by match
    @app.get("/chat/match/<match_id>")
    def get_messages_by_match(match_id):
        rows = session.execute(
            "SELECT * FROM chat_messages_by_room WHERE match_id = %s",
            [match_id]
        )
        messages = [{
            "messageId": str(r.message_id),
            "userId": r.user_id,
            "userEmail": r.user_email,
            "message": r.message,
            "sentAt": r.sent_at.isoformat()
        } for r in rows]
        return jsonify({"matchId": match_id, "messages": messages})

    @app.get("/chat/user/<user_id>")
    def get_messages_by_user(user_id):
        rows = session.execute(
            "SELECT * FROM chat_messages_by_user WHERE user_id = %s",
            [user_id]
        )
        messages = [{
            "messageId": str(r.message_id),
            "matchId": r.match_id,
            "message": r.message,
            "sentAt": r.sent_at.isoformat()
        } for r in rows]
        return jsonify({"userId": user_id, "messages": messages})

    from datetime import datetime

    @app.get("/chat/user/<user_id>/day/<day_str>")
    def get_messages_by_user_day(user_id, day_str):
        """
        Get all chat messages for a specific user on a specific day.
        Example: /chat/user/68f27893e6f79eef77a5c165/day/2025-11-08
        """
        try:
            day = datetime.strptime(day_str, "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

        rows = session.execute("""
            SELECT * FROM chat_messages_by_user_day WHERE user_id = %s AND day = %s
        """, (user_id, day))

        messages = [{
            "messageId": str(r.message_id),
            "matchId": r.match_id,
            "message": r.message,
            "sentAt": r.sent_at.isoformat()
        } for r in rows]

        return jsonify({
            "userId": user_id,
            "day": day_str,
            "messages": messages
        })

    # CLEAR test data
    @app.delete("/chat/clear")
    def clear_chat_data():
        session.execute("TRUNCATE chat_messages_by_room;")
        session.execute("TRUNCATE chat_messages_by_user_day;")
        session.execute("TRUNCATE chat_messages_by_user;")
        return jsonify({"message": "All chat messages deleted"}), 200

    @app.get("/chat/health")
    def health_check():
        return jsonify({"ok": True, "source": "Cassandra", "ttl": "2 days"})
