from flask import request, jsonify
from bson import ObjectId
from bson.decimal128 import Decimal128
from decimal import Decimal
from datetime import datetime
from collections import OrderedDict
import json
from flask import Response

def register_bets_routes(app, db):
    BETS = db.Bets

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
        if "bet" in d:
            if "stake" in d["bet"]:
                d["bet"]["stake"] = to_float(d["bet"]["stake"])
            if "odds" in d["bet"]:
                d["bet"]["odds"] = to_float(d["bet"]["odds"])
        return d

    @app.get("/bets")
    def list_bets():
        status = request.args.get("status")
        sort_by = request.args.get("sort_by")
        ascending = request.args.get("ascending", "true").lower() == "true"
        team = request.args.get("team")
        event_start = request.args.get("event_start_date")
        event_end = request.args.get("event_end_date")
        created_start = request.args.get("created_start_date")
        created_end = request.args.get("created_end_date")

        query = {}

        if status:
            query["status"] = status

        if team:
            query["$or"] = [
                {"event.team_1": team},
                {"event.team_2": team}
            ]

        if event_start or event_end:
            date_query = {}
            try:
                if event_start:
                    date_query["$gte"] = datetime.strptime(event_start, "%Y-%m-%d")
                if event_end:
                    date_query["$lte"] = datetime.strptime(event_end, "%Y-%m-%d")
                query["event.date"] = date_query
            except ValueError:
                return jsonify({"message": "Invalid event date format. Use YYYY-MM-DD"}), 400

        if created_start or created_end:
            created_query = {}
            try:
                if created_start:
                    created_query["$gte"] = datetime.strptime(created_start, "%Y-%m-%d")
                if created_end:
                    created_query["$lte"] = datetime.strptime(created_end, "%Y-%m-%d")
                query["bet.createdAt"] = created_query
            except ValueError:
                return jsonify({"message": "Invalid createdAt date format. Use YYYY-MM-DD"}), 400

        sort_field_map = {
            "stake": "bet.stake",
            "odds": "bet.odds",
            "event_date": "event.date",
            "createdAt": "bet.createdAt"
        }
        sort_field = sort_field_map.get(sort_by)
        sort_order = 1 if ascending else -1

        cur = BETS.find(query)
        if sort_field:
            cur = cur.sort(sort_field, sort_order)

        items = [ser(x) for x in cur]
        total = len(items)
        return jsonify({"items": items, "total": total})

    @app.get("/bets/by_email/<email>")
    def get_bets_by_email(email):
        status = request.args.get("status")
        team = request.args.get("team")
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")

        query = {"userEmail": email}

        if status:
            query["status"] = status
        if team:
            query["$or"] = [{"event.team_1": team}, {"event.team_2": team}]
        if start_date or end_date:
            date_query = {}
            if start_date:
                date_query["$gte"] = start_date
            if end_date:
                date_query["$lte"] = end_date
            query["event.date.$date"] = date_query

        cur = BETS.find(query)
        items = [ser(x) for x in cur]
        if not items:
            return jsonify({"error": "No bets found for this email"}), 404
        return jsonify({"items": items, "total": len(items)})

    @app.post("/bets")
    def create_bet():
        try:
            data = request.get_json(silent=True) or {}
            now = datetime.utcnow()
            data.setdefault("createdAt", now)
            data.setdefault("status", "pending")

            if "userId" in data and isinstance(data["userId"], str):
                data["userId"] = ObjectId(data["userId"])

            user_email = data.get("userEmail")
            event = data.get("event", {})
            team_1 = event.get("team_1")
            team_2 = event.get("team_2")

            if not user_email or not team_1 or not team_2:
                return jsonify({
                    "message": "Missing required fields (userEmail, event.team_1, or event.team_2)"
                }), 400

            existing_bet = BETS.find_one({
                "userEmail": user_email,
                "event.team_1": team_1,
                "event.team_2": team_2
            })

            if existing_bet:
                return jsonify({
                    "message": "You have already placed a bet for this event.",
                    "bet": ser(existing_bet)
                }), 400

            res = BETS.insert_one(data)
            new_bet = BETS.find_one({"_id": res.inserted_id})

            return jsonify({
                "message": "Bet added successfully",
                "bet": ser(new_bet)
            }), 201

        except Exception as e:
            return jsonify({
                "message": "Failed to add bet",
                "error": str(e)
            }), 400

    @app.delete("/bets/<id>")
    def delete_bet(id):
        oid = to_oid(id)
        if not oid:
            return jsonify({"error": "Invalid id"}), 400
        res = BETS.delete_one({"_id": oid})
        if not res.deleted_count:
            return jsonify({"error": "Not found"}), 404
        return jsonify({"deleted": True, "_id": id})

    @app.get("/bets/summary")
    def bet_summary():
        summary = {}
        for b in BETS.find({}):
            email = b["userEmail"]
            stake = to_float(b["bet"]["stake"])
            odds = to_float(b["bet"]["odds"])
            amount = Decimal(str(stake * odds))

            if email not in summary:
                summary[email] = {"total_won": Decimal("0"), "total_lost": Decimal("0")}

            if b["status"] == "won":
                summary[email]["total_won"] += amount
            elif b["status"] == "lost":
                summary[email]["total_lost"] += amount

        output = []
        for email, vals in summary.items():
            final_balance = vals["total_won"] - vals["total_lost"]
            output.append(OrderedDict([
                ("userEmail", email),
                ("total_won", round(float(vals["total_won"]), 2)),
                ("total_lost", round(float(vals["total_lost"]), 2)),
                ("final_balance", round(float(final_balance), 2))
            ]))

        return Response(json.dumps(output), mimetype='application/json')