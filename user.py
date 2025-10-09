from flask import request, jsonify
from bson import ObjectId
from bson.decimal128 import Decimal128
from decimal import Decimal
from datetime import datetime

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
        sort_field = sort_field_map.get(sort_by)

        if sort_field:
            sort_order = 1 if ascending else -1
            cur = USERS.find(query).sort(sort_field, sort_order)
        else:
            cur = USERS.find(query)

        items = [ser(x) for x in cur]
        return jsonify({"items": items, "total": len(items)})

    @app.get("/users/<id>")
    def get_user(id):
        oid = to_oid(id)
        if not oid:
            return jsonify({"error": "Invalid id"}), 400
        user = USERS.find_one({"_id": oid})
        if not user:
            return jsonify({"error": "User not found"}), 404
        return jsonify({"user": ser(user)})

    from flask import request, jsonify
    from bson.decimal128 import Decimal128
    from datetime import datetime
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

            # 5) papildomi laukai
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

            # saugokime sukūrimo laiką
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

    @app.delete("/users/<id>")
    def delete_user(id):
        oid = to_oid(id)
        if not oid:
            return jsonify({"error": "Invalid id"}), 400
        res = USERS.delete_one({"_id": oid})
        if not res.deleted_count:
            return jsonify({"error": "User not found"}), 404
        return jsonify({"deleted": True, "_id": id})

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

        res = USERS.update_one({"_id": oid}, {"$set": {"balance": Decimal128(str(new_balance))}})
        if res.modified_count == 0:
            return jsonify({"error": "No user updated"}), 404

        return jsonify({"message": "User balance updated", "userId": user_id, "balance": float(new_balance)})