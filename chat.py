from flask import request, jsonify
from cassandra.cluster import Cluster
from datetime import datetime, date
import uuid
from bson import ObjectId

def register_chat_routes(app, db):
    MATCHES = db.Matches   # collection
    USERS = db.User

    # ===== Cassandra connection =====
    cluster = Cluster(['localhost'])
    session = cluster.connect('sportsbook')

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

    # ---- CREATE ----
    @app.post("/chat/messages")
    def create_message():
        data = request.get_json(silent=True) or {}
        match_id = data.get("matchId")
        user_id = data.get("userId")
        user_email = data.get("userEmail")
        message_text = data.get("message")

        if not all([match_id, user_id, user_email, message_text]):
            return jsonify({"error": "matchId, userId, userEmail, and message are required"}), 400

        # Check user and match existent
        if not match_exists(match_id):
            return jsonify({"error": f"Match {match_id} not found in Mongo"}), 404
        if not user_exists(user_id):
            return jsonify({"error": f"User {user_id} not found in Mongo"}), 404

        message_id = uuid.uuid4()
        sent_at = datetime.now()
        day = date.today()
        ttl_seconds = 172800  # 2 days

        # Input in Cassandra
        session.execute("""
            INSERT INTO chat_messages_by_room (match_id, message_id, user_id, user_email, message, sent_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            USING TTL %s
        """, (match_id, message_id, user_id, user_email, message_text, sent_at, ttl_seconds))

        session.execute("""
            INSERT INTO chat_messages_by_user_day (user_id, day, message_id, match_id, message, sent_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            USING TTL %s
        """, (user_id, day, message_id, match_id, message_text, sent_at, ttl_seconds))

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
    # ---- READ ----
    @app.get("/chat/match/<match_id>")
    def get_messages_by_match(match_id):
        rows = session.execute("SELECT * FROM chat_messages_by_room WHERE match_id = %s", [match_id])
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
        rows = session.execute("""
            SELECT * FROM chat_messages_by_user_day
            WHERE user_id = %s ALLOW FILTERING
        """, [user_id])
        today = date.today()
        messages = [{
            "messageId": str(r.message_id),
            "matchId": r.match_id,
            "message": r.message,
            "sentAt": r.sent_at.isoformat()
        } for r in rows if r.day == today]
        return jsonify({"userId": user_id, "messages": messages})

    # ---- UPDATE ----
    @app.patch("/chat/messages/<message_id>")
    def update_message(message_id):
        data = request.get_json(silent=True) or {}
        new_text = data.get("message")
        if not new_text:
            return jsonify({"error": "New message text required"}), 400


        return jsonify({"message": "Direct updates are not supported in Cassandra (immutable records)."}), 400

    # ---- DELETE ----
    @app.delete("/chat/messages/<message_id>")
    def delete_message(message_id):
        return jsonify({"message": "Delete by message_id not supported; use TTL auto-expiry (2 days)."}), 400

    @app.delete("/chat/clear")
    def clear_chat_data():
        session.execute("TRUNCATE chat_messages_by_room;")
        session.execute("TRUNCATE chat_messages_by_user_day;")
        return jsonify({"message": "All chat messages deleted"}), 200

    @app.get("/chat/health")
    def health_check():
        return jsonify({"ok": True, "source": "Cassandra", "ttl": "2 days"})
