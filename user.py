from flask import request, jsonify
from bson import ObjectId
from bson.decimal128 import Decimal128
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
def register_users_routes(app, db):
    USERS = db.User

    def to_oid(s):
        try:
            return ObjectId(s)
        except Exception:
            return None

    def to_float(val):
        if isinstance(val, Decimal128):
            return float(val.to_decimal())
        if isinstance(val, Decimal):
            return float(val)
        return val

    def ser(doc):
        if not doc:
            return None
        d = dict(doc)
        for k, v in d.items():
            if isinstance(v, ObjectId):
                d[k] = str(v)
            elif isinstance(v, dict):
                d[k] = ser(v)
            elif isinstance(v, list):
                d[k] = [ser(x) if isinstance(x, dict) else x for x in v]
            elif isinstance(v, Decimal128):
                d[k] = float(v.to_decimal())
        if "balance" in d:
            d["balance"] = to_float(d["balance"])
        if "birthDate" in d and isinstance(d["birthDate"], dict) and "$date" in d["birthDate"]:
            d["birthDate"] = d["birthDate"]["$date"]
        return d

    @app.get("/users")
    def list_users():
        first_name = request.args.get("firstName")
        last_name = request.args.get("lastName")
        min_balance = request.args.get("min_balance", type=float)
        max_balance = request.args.get("max_balance", type=float)
        sort_by = request.args.get("sort_by")
        ascending = request.args.get("ascending", "true").lower() == "true"

        query = {}
        if first_name:
            query["firstName"] = {"$regex": first_name, "$options": "i"}
        if last_name:
            query["lastName"] = {"$regex": last_name, "$options": "i"}
        if min_balance is not None or max_balance is not None:
            balance_query = {}
            if min_balance is not None:
                balance_query["$gte"] = Decimal128(str(min_balance))
            if max_balance is not None:
                balance_query["$lte"] = Decimal128(str(max_balance))
            query["balance"] = balance_query

        sort_field_map = {
            "balance": "balance",
            "firstName": "firstName",
            "lastName": "lastName"
        }
        sort_field = sort_field_map.get(sort_by) or "_id"
        order = 1 if ascending else -1

        total = USERS.count_documents(query)  # ← total skaičiuoja Mongo
        cur = (USERS.find(query).sort(sort_field, order))
        items = [ser(x) for x in cur]
        return jsonify({"items": items, "total": total})

    @app.get("/users/<id>")
    def get_user(id):
        oid = to_oid(id)
        if not oid:
            return jsonify({"error": "Invalid id"}), 400
        user = USERS.find_one({"_id": oid})
        if not user:
            return jsonify({"error": "User not found"}), 404
        return jsonify({"user": ser(user)})

    import re

    EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    PHONE_RE = re.compile(r"^\+?\d{7,20}$")
    IBAN_RE = re.compile(r"^[A-Z0-9]{15,34}$")

    REQUIRED_FIELDS = ["email", "nickname", "firstName", "lastName", "phone", "IBAN"]

    def norm_email(s):
        return (s or "").strip().lower()

    def norm_nickname(s):
        return (s or "").strip()

    def norm_phone(s):
        # paliekam tik + ir skaitmenis
        s = (s or "").strip().replace(" ", "").replace("-", "")
        if s.startswith("00"):
            s = "+" + s[2:]
        return s

    def norm_iban(s):
        return (s or "").replace(" ", "").upper()

    @app.post("/users")
    def create_user():
        try:
            raw = request.get_json(silent=True) or {}
            data = {}

            # 1) paimame laukus ir normalizuojame
            data["email"] = norm_email(raw.get("email"))
            data["nickname"] = norm_nickname(raw.get("nickname"))
            data["firstName"] = (raw.get("firstName") or "").strip()
            data["lastName"] = (raw.get("lastName") or "").strip()
            data["phone"] = norm_phone(raw.get("phone"))
            data["IBAN"] = norm_iban(raw.get("IBAN"))

            # 2) patikrinam privalomus laukus
            missing = [f for f in REQUIRED_FIELDS if not data.get(f)]
            if missing:
                return jsonify({
                    "message": "Missing required fields.",
                    "missing": missing
                }), 400

            # 3) formatų validacija
            errors = {}
            if not EMAIL_RE.match(data["email"]):
                errors["email"] = "Invalid email format."
            if not PHONE_RE.match(data["phone"]):
                errors["phone"] = "Invalid phone format. Use international format (e.g., +370...)."
            if not IBAN_RE.match(data["IBAN"]):
                errors["IBAN"] = "Invalid IBAN format."
            if errors:
                return jsonify({"message": "Validation error.", "errors": errors}), 400

            # 4) dublikato patikra pagal pateiktus laukus
            or_clauses = []
            for key in ["email", "nickname", "phone", "IBAN"]:
                if data.get(key):
                    or_clauses.append({key: data[key]})
            if or_clauses:
                duplicate = USERS.find_one({"$or": or_clauses})
                if duplicate:
                    return jsonify({
                        "message": "User with the same email, nickname, phone number, or IBAN already exists."
                    }), 400

            # balance → Decimal128 (jei pateiktas)
            if "balance" in raw and raw["balance"] is not None:
                try:
                    data["balance"] = Decimal128(str(raw["balance"]))
                except Exception:
                    return jsonify({"message": "Invalid balance value."}), 400

            # birthDate → datetime (YYYY-MM-DD)
            if "birthDate" in raw and raw["birthDate"]:
                try:
                    data["birthDate"] = datetime.strptime(raw["birthDate"], "%Y-%m-%d")
                except Exception:
                    return jsonify({"message": "Invalid birthDate format. Use YYYY-MM-DD."}), 400
            data.setdefault("createdAt", datetime.utcnow())

            # 6) įrašymas
            res = USERS.insert_one(data)
            new_user = USERS.find_one({"_id": res.inserted_id})

            return jsonify({
                "message": "User added successfully",
                "user": ser(new_user)
            }), 201

        except Exception as e:
            return jsonify({
                "message": "Failed to add user",
                "error": str(e)
            }), 400


    @app.patch("/users/<id>")
    def patch_user(id):
        oid = to_oid(id)
        if not oid:
            return jsonify({"error": "Invalid id"}), 400

        payload = request.get_json(silent=True) or {}
        if not isinstance(payload, dict) or not payload:
            return jsonify({"error": "Empty or invalid body"}), 400

        # Leidžiami laukai atnaujinimui
        allowed = {"firstName", "lastName", "nickname", "phone", "IBAN", "balance", "birthDate"}
        updates = {k: v for k, v in payload.items() if k in allowed}
        if not updates:
            return jsonify({"error": "No allowed fields to update", "allowed": list(allowed)}), 400

        # Normalizacijos:
        if "balance" in updates:
            try:
                updates["balance"] = Decimal128(str(updates["balance"]))
            except Exception:
                return jsonify({"error": "Invalid balance"}), 400

        if "birthDate" in updates and updates["birthDate"]:
            try:
                updates["birthDate"] = datetime.strptime(updates["birthDate"], "%Y-%m-%d")
            except Exception:
                return jsonify({"error": "Invalid birthDate. Use YYYY-MM-DD"}), 400

        if "phone" in updates:
            p = (updates["phone"] or "").replace(" ", "").replace("-", "")
            if p.startswith("00"):
                p = "+" + p[2:]
            updates["phone"] = p

        if "IBAN" in updates:
            updates["IBAN"] = (updates["IBAN"] or "").replace(" ", "").upper()

        res = USERS.update_one({"_id": oid}, {"$set": updates})
        if res.matched_count == 0:
            return jsonify({"error": "User not found"}), 404

        user = USERS.find_one({"_id": oid})
        return jsonify({"message": "User updated", "user": ser(user)}), 200

    @app.post("/users/update_balance")
    def update_user_balance():
        data = request.get_json(silent=True) or {}
        user_id = data.get("userId")
        new_balance = data.get("balance")
        if not user_id or new_balance is None:
            return jsonify({"error": "Missing userId or balance"}), 400

        oid = to_oid(user_id)
        if not oid:
            return jsonify({"error": "Invalid userId"}), 400

        try:
            dec = Decimal(str(new_balance)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        except (InvalidOperation, TypeError, ValueError):
            return jsonify({"error": "Invalid balance format"}), 400

        res = USERS.update_one({"_id": oid}, {"$set": {"balance": Decimal128(dec)}})
        if res.matched_count == 0:
            return jsonify({"error": "User not found"}), 404

        return jsonify({"message": "User balance updated", "userId": user_id, "balance": str(dec)}), 200

    @app.get("/users/by_email/<email>")
    def get_user_by_email(email):
        user = USERS.find_one({"email": (email or "").strip().lower()})
        if not user:
            return jsonify({"error": "User not found"}), 404
        return jsonify({"user": ser(user)}), 200

    @app.delete("/users/<id>")
    def delete_user(id):
        oid = to_oid(id)
        if not oid:
            return jsonify({"error": "Invalid id"}), 400
        res = USERS.delete_one({"_id": oid})
        if not res.deleted_count:
            return jsonify({"error": "User not found"}), 404
        return jsonify({"deleted": True, "_id": id})