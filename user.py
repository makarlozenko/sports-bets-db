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

    @app.post("/users")
    def create_user():
        try:
            data = request.get_json(silent=True) or {}

            email = data.get("email")
            nickname = data.get("nickname")
            phone = data.get("phone")
            iban = data.get("IBAN")

            duplicate_check = USERS.find_one({
                "$or": [
                    {"email": email},
                    {"nickname": nickname},
                    {"phone": phone},
                    {"IBAN": iban}
                ]
            })

            if duplicate_check:
                return jsonify({
                    "message": "User with the same email, nickname, phone number, or IBAN already exists."
                }), 400

            if "balance" in data:
                data["balance"] = Decimal128(str(data["balance"]))

            if "birthDate" in data:
                try:
                    data["birthDate"] = {"$date": datetime.strptime(data["birthDate"], "%Y-%m-%d")}
                except Exception:
                    return jsonify({"error": "Invalid birthDate format. Use YYYY-MM-DD"}), 400

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