from flask import request, jsonify
from bson import ObjectId
from bson.decimal128 import Decimal128
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from datetime import datetime, timedelta, timezone
import json
import redis
import uuid

# Cart stored in Redis as Hash: key = "app:cart:user:<id_or_email>"
# field = item_id (uuid), value = JSON string of the item
# Rolling TTL (touch on every operatio  n)

REDIS_HOST = "localhost"
REDIS_PORT = 6379
CART_TTL_SECONDS = 3 * 24 * 3600  # 3 days

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

def _cart_key(user_key: str) -> str:
    return f"app:cart:user:{user_key}"

def _touch_ttl(key: str):
    r.expire(key, CART_TTL_SECONDS)

def _ensure_user_key(data):
    user_id = data.get("userId")
    user_email = data.get("userEmail")
    if user_id:
        return str(user_id)
    if user_email:
        return user_email.strip().lower()
    return None

def register_cart_routes(app, db):
    USERS = db.User
    BETS = db.Bets
    MATCHES = db.Matches

    # ---------- Helpers ----------
    def to_oid(s):
        try:
            return ObjectId(s)
        except Exception:
            return None

    def ser_oid(x):
        if isinstance(x, ObjectId):
            return str(x)
        return x

    def _parse_ymd(s):
        try:
            return datetime.strptime(s, "%Y-%m-%d")
        except Exception:
            return None

    def _event_date_to_storage(raw):
        # accept "YYYY-MM-DD" or ISO-8601; store as string when YYYY-MM-DD else naive UTC datetime
        txt = str(raw).strip()
        if txt and len(txt) == 10:
            return txt
        try:
            dt = datetime.fromisoformat(txt.replace("Z","+00:00"))
            return dt.astimezone(timezone.utc).replace(tzinfo=None)
        except Exception:
            return txt  # last resort; keep as is

    # ---------- CRUD ----------
    @app.post("/cart/items")
    def cart_add_item():
        payload = request.get_json(silent=True) or {}
        user_key = _ensure_user_key(payload)
        item = payload.get("item") or {}
        if not user_key:
            return jsonify({"error": "Provide userId or userEmail"}), 400
        # minimal validation
        ev = item.get("event") or {}
        bet = item.get("bet") or {}
        if not ev.get("team_1") or not ev.get("team_2") or not ev.get("date"):
            return jsonify({"error": "item.event.team_1, team_2 and date are required"}), 400
        if not bet.get("choice"):
            return jsonify({"error": "item.bet.choice is required"}), 400
        if "stake" not in bet:
            return jsonify({"error": "item.bet.stake is required"}), 400
        try:
            stake_dec = Decimal(str(bet.get("stake"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if stake_dec <= Decimal("0"):
                raise InvalidOperation()
        except Exception:
            return jsonify({"error": "Invalid stake"}), 400

        # normalize date
        item["event"]["date"] = _event_date_to_storage(ev.get("date"))
        item_id = str(uuid.uuid4())

        key = _cart_key(user_key)
        r.hset(key, item_id, json.dumps(item))
        _touch_ttl(key)

        return jsonify({"message": "Added to cart", "itemId": item_id, "item": item}), 201

    @app.get("/cart")
    def cart_get():
        user_key = request.args.get("user") or ""
        if not user_key:
            return jsonify({"error": "Missing ?user="}), 400
        key = _cart_key(user_key)
        data = r.hgetall(key)
        if not data:
            return jsonify({"items": [], "total": 0, "ttl": r.ttl(key)}), 200
        items = [{"id": k, "item": json.loads(v)} for k, v in data.items()]
        _touch_ttl(key)
        return jsonify({"items": items, "total": len(items), "ttl": r.ttl(key)}), 200

    @app.patch("/cart/items/<item_id>")
    def cart_update_item(item_id):
        payload = request.get_json(silent=True) or {}
        user_key = _ensure_user_key(payload)
        if not user_key:
            return jsonify({"error": "Provide userId or userEmail"}), 400
        key = _cart_key(user_key)
        raw = r.hget(key, item_id)
        if not raw:
            return jsonify({"error": "Item not found"}), 404
        item = json.loads(raw)
        updates = payload.get("item") or {}
        # simple merge
        for k in ["event", "bet"]:
            if k in updates and isinstance(updates[k], dict):
                item.setdefault(k, {}).update(updates[k])
        if "event" in item and "date" in item["event"]:
            item["event"]["date"] = _event_date_to_storage(item["event"]["date"])
        r.hset(key, item_id, json.dumps(item))
        _touch_ttl(key)
        return jsonify({"message": "Updated", "id": item_id, "item": item}), 200

    @app.delete("/cart/items/<item_id>")
    def cart_delete_item(item_id):
        user_key = request.args.get("user") or ""
        if not user_key:
            return jsonify({"error": "Missing ?user="}), 400
        key = _cart_key(user_key)
        removed = r.hdel(key, item_id)
        _touch_ttl(key)
        return jsonify({"deleted": bool(removed), "id": item_id}), 200

    @app.delete("/cart/clear")
    def cart_clear():
        user_key = request.args.get("user") or ""
        if not user_key:
            return jsonify({"error": "Missing ?user="}), 400
        key = _cart_key(user_key)
        r.delete(key)
        return jsonify({"cleared": True}), 200

    # ---------- CHECKOUT ----------
    # Persist all cart items into Mongo Bets and clear cart.
    # Ensures final state consistency: validates user balance >= total stake, deducts once.
    @app.post("/cart/checkout")
    def cart_checkout():
        payload = request.get_json(silent=True) or {}
        user_id = payload.get("userId")
        user_email = (payload.get("userEmail") or "").strip().lower()
        user_key = _ensure_user_key(payload)
        if not user_key:
            return jsonify({"error": "Provide userId or userEmail"}), 400
        key = _cart_key(user_key)
        data = r.hgetall(key)
        if not data:
            return jsonify({"error": "Cart is empty"}), 400

        # Load and validate items
        items = [json.loads(v) for v in data.values()]
        try:
            stakes = [Decimal(str(it.get("bet", {}).get("stake", "0"))) for it in items]
            total_stake = sum(stakes)
            total_stake = Decimal(total_stake).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        except Exception:
            return jsonify({"error": "Invalid stakes in cart"}), 400
        if total_stake <= Decimal("0"):
            return jsonify({"error": "Total stake must be > 0"}), 400

        # Select user by id or email
        selector = {"_id": ObjectId(user_id)} if user_id else {"email": user_email}
        # Deduct balance if enough
        user_after = USERS.find_one_and_update(
            {**selector, "balance": {"$gte": Decimal128(str(total_stake))}},
            {"$inc": {"balance": Decimal128(str(-total_stake))}},
            return_document=True
        )
        if not user_after:
            return jsonify({"error": "Insufficient balance or user not found."}), 400

        inserted_ids = []
        try:
            now = datetime.utcnow()
            for it in items:
                # Normalize payload to bets schema (minimal)
                doc = {
                    "userEmail": user_email or user_after.get("email"),
                    "userId": user_after.get("_id"),
                    "event": {
                        "team_1": it.get("event", {}).get("team_1"),
                        "team_2": it.get("event", {}).get("team_2"),
                        "type": (it.get("event", {}).get("type") or ""),
                        "date": it.get("event", {}).get("date"),
                    },
                    "bet": {
                        k: v for k, v in (it.get("bet") or {}).items() if k != "odds"
                    },
                    "status": "pending",
                    "createdAt": now
                }
                # ensure Decimal128 for stake
                if "stake" in doc["bet"]:
                    doc["bet"]["stake"] = Decimal128(str(Decimal(str(doc["bet"]["stake"])).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)))
                res = BETS.insert_one(doc)
                inserted_ids.append(res.inserted_id)

            # success → clear cart
            r.delete(key)
            return jsonify({
                "message": "Checkout successful",
                "count": len(inserted_ids),
                "betIds": [str(x) for x in inserted_ids]
            }), 201
        except Exception as e:
            # rollback: delete inserted bets and refund
            if inserted_ids:
                BETS.delete_many({"_id": {"$in": inserted_ids}})
            USERS.update_one(selector, {"$inc": {"balance": Decimal128(str(total_stake))}})
            return jsonify({"error": "Checkout failed", "details": str(e)}), 500



