from bson import ObjectId
from bson.decimal128 import Decimal128
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from collections import OrderedDict
from flask import Response, request, jsonify
import json
import re

YYYY_MM_DD_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
VALID_CHOICES = {"winner", "score"}

def register_bets_routes(app, db):
    BETS = db.Bets
    MATCHES = db.Matches

    # ---------- helpers ----------
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

    def ser(x):
        if x is None:
            return None
        if isinstance(x, ObjectId):
            return str(x)
        if isinstance(x, datetime):
            return x.isoformat()
        if isinstance(x, Decimal128):
            return float(x.to_decimal())
        if isinstance(x, dict):
            return {k: ser(v) for k, v in x.items()}
        if isinstance(x, list):
            return [ser(v) for v in x]
        return x

    def _parse_ymd(s):
        try:
            return datetime.strptime(s, "%Y-%m-%d")
        except Exception:
            return None

    def _day_bounds_naive(dt):
        """[00:00, 24:00) tos dienos, NAIVE (Mongo Date laukas be tzinfo)."""
        d0 = datetime(dt.year, dt.month, dt.day)
        return d0, d0 + timedelta(days=1)

    def _norm_name(s: str) -> str:
        return (s or "").strip()

    def _parse_event_date(s):
        """Grąžina AWARE UTC datetime, jei pavyksta, kitaip - None."""
        if s is None:
            return None
        if isinstance(s, datetime):
            dt = s
        else:
            txt = str(s).strip()
            try:
                if txt.endswith("Z"):
                    dt = datetime.strptime(txt, "%Y-%m-%dT%H:%M:%S.%fZ")
                    return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                pass
            for fmt in ["%Y-%m-%dT%H:%M:%S%z",
                        "%Y-%m-%dT%H:%M:%S.%f%z",
                        "%Y-%m-%d"]:
                try:
                    dt = datetime.strptime(txt, fmt)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt.astimezone(timezone.utc)
                except ValueError:
                    continue
        return None

    def _storage_date(event_date_raw, event_dt):
        """Jei klientas davė 'YYYY-MM-DD' – saugom kaip string; kitu atveju – naive UTC datetime."""
        if isinstance(event_date_raw, str) and YYYY_MM_DD_RE.match(event_date_raw.strip()):
            return event_date_raw.strip()
        return event_dt.astimezone(timezone.utc).replace(tzinfo=None)

    # ---------- LIST ----------
    @app.get("/bets")
    def list_bets():
        status         = request.args.get("status")
        sort_by        = request.args.get("sort_by")
        ascending_str  = (request.args.get("ascending") or "true").lower()
        team           = request.args.get("team")
        event_start    = request.args.get("event_start_date")
        event_end      = request.args.get("event_end_date")
        created_start  = request.args.get("created_start_date")
        created_end    = request.args.get("created_end_date")
        try:
            limit = int(request.args.get("limit", 100))
            skip  = int(request.args.get("skip", 0))
        except ValueError:
            return jsonify({"message": "limit/skip must be integers"}), 400

        ascending = ascending_str in ("1", "true", "yes", "y")

        query = {}

        if status:
            query["status"] = status

        if team:
            rx = {"$regex": f"^{re.escape(team.strip())}$", "$options": "i"}
            query["$or"] = [{"event.team_1": rx}, {"event.team_2": rx}]

        #Event date interval (Date ir (arba) String)
        event_or = []

        #Date interval (Mongo Date)
        date_range_dt = {}
        if event_start:
            d = _parse_ymd(event_start)
            if not d: return jsonify({"message": "Invalid event_start_date. Use YYYY-MM-DD"}), 400
            d0, _ = _day_bounds_naive(d)
            date_range_dt["$gte"] = d0
        if event_end:
            d = _parse_ymd(event_end)
            if not d: return jsonify({"message": "Invalid event_end_date. Use YYYY-MM-DD"}), 400
            _, d1 = _day_bounds_naive(d)
            date_range_dt["$lte"] = d1
        if date_range_dt:
            event_or.append({"event.date": date_range_dt})

        # String range (YYYY-MM-DD)
        date_range_str = {}
        if event_start:
            if not YYYY_MM_DD_RE.match(event_start):
                return jsonify({"message": "Invalid event_start_date. Use YYYY-MM-DD"}), 400
            date_range_str["$gte"] = event_start
        if event_end:
            if not YYYY_MM_DD_RE.match(event_end):
                return jsonify({"message": "Invalid event_end_date. Use YYYY-MM-DD"}), 400
            date_range_str["$lte"] = event_end
        if date_range_str:
            event_or.append({"event.date": date_range_str})

        if event_or:
            if "$or" in query:
                query["$and"] = [{"$or": query.pop("$or")}, {"$or": event_or}]
            else:
                query["$or"] = event_or

        # Created date interval – tikriname ir top-level createdAt, ir bet.createdAt
        created_or = []
        created_range = {}
        if created_start:
            d = _parse_ymd(created_start)
            if not d: return jsonify({"message": "Invalid created_start_date. Use YYYY-MM-DD"}), 400
            d0, _ = _day_bounds_naive(d)
            created_range["$gte"] = d0
        if created_end:
            d = _parse_ymd(created_end)
            if not d: return jsonify({"message": "Invalid created_end_date. Use YYYY-MM-DD"}), 400
            _, d1 = _day_bounds_naive(d)
            created_range["$lte"] = d1
        if created_range:
            created_or.append({"createdAt": created_range})
            created_or.append({"bet.createdAt": created_range})
            if "$and" in query:
                query["$and"].append({"$or": created_or})
            elif "$or" in query:
                query = {"$and": [{"$or": query.pop("$or")}, {"$or": created_or}]}
            else:
                query["$or"] = created_or

        sort_field_map = {
            "stake": "bet.stake",
            "odds": "bet.odds",
            "event_date": "event.date",
            "createdAt": "createdAt",
            "bet_createdAt": "bet.createdAt",
        }
        sort_field = sort_field_map.get(sort_by)
        sort_order = 1 if ascending else -1

        cur = BETS.find(query)
        if sort_field:
            cur = cur.sort(sort_field, sort_order)
        cur = cur.skip(max(0, skip)).limit(max(1, min(limit, 1000)))

        items = [ser(x) for x in cur]
        return jsonify({
            "items": items,
            "total": len(items),
            "query": query,
            "sorted_by": sort_field,
            "ascending": ascending,
            "limit": limit,
            "skip": skip
        })

    # ---------- BY EMAIL ----------
    @app.get("/bets/by_email/<email>")
    def get_bets_by_email(email):
        status      = request.args.get("status")
        team        = request.args.get("team")
        start_date  = request.args.get("start_date")
        end_date    = request.args.get("end_date")

        query = {"userEmail": email}

        if status:
            query["status"] = status

        if team:
            rx = {"$regex": f"^{re.escape(team.strip())}$", "$options": "i"}
            query["$or"] = [{"event.team_1": rx}, {"event.team_2": rx}]

        # range ant event.date kaip Date ir kaip String tipai
        or_date = []
        if start_date or end_date:
            # Date
            rng_dt = {}
            if start_date:
                d = _parse_ymd(start_date)
                if not d: return jsonify({"message": "Invalid start_date. Use YYYY-MM-DD"}), 400
                d0, _ = _day_bounds_naive(d)
                rng_dt["$gte"] = d0
            if end_date:
                d = _parse_ymd(end_date)
                if not d: return jsonify({"message": "Invalid end_date. Use YYYY-MM-DD"}), 400
                _, d1 = _day_bounds_naive(d)
                rng_dt["$lte"] = d1
            if rng_dt:
                or_date.append({"event.date": rng_dt})

            # String
            rng_str = {}
            if start_date:
                if not YYYY_MM_DD_RE.match(start_date):
                    return jsonify({"message": "Invalid start_date. Use YYYY-MM-DD"}), 400
                rng_str["$gte"] = start_date
            if end_date:
                if not YYYY_MM_DD_RE.match(end_date):
                    return jsonify({"message": "Invalid end_date. Use YYYY-MM-DD"}), 400
                rng_str["$lte"] = end_date
            if rng_str:
                or_date.append({"event.date": rng_str})

            if or_date:
                query = {"$and": [ {"userEmail": email}, {"$or": or_date} , *( [{"$or": query["$or"]}] if "$or" in query else [] ) ]}
            else:
                query = {"userEmail": email, **({"$or": query["$or"]} if "$or" in query else {})}

        cur = BETS.find(query)
        items = [ser(x) for x in cur]
        if not items:
            return jsonify({"error": "No bets have been found for this email."}), 404
        return jsonify({"items": items, "total": len(items)})

    # ---------- CREATE ----------
    @app.post("/bets")
    def create_bet():
        try:
            payload = request.get_json(silent=True) or {}

            user_email = (payload.get("userEmail") or "").strip().lower()
            user_id    = payload.get("userId")
            event      = payload.get("event") or {}
            bet        = payload.get("bet") or {}

            team_1 = _norm_name(event.get("team_1"))
            team_2 = _norm_name(event.get("team_2"))
            event_date_raw = event.get("date")
            event_dt = _parse_event_date(event_date_raw)

            missing = []
            if not user_email: missing.append("userEmail")
            if not team_1:     missing.append("event.team_1")
            if not team_2:     missing.append("event.team_2")
            if not event_dt:   missing.append("event.date (ISO-8601 or YYYY-MM-DD)")
            if not bet.get("choice"): missing.append("bet.choice")
            if missing:
                return jsonify({"message": "Missing required fields,", "missing": missing}), 400

            if user_id and isinstance(user_id, str):
                try:
                    user_id = ObjectId(user_id)
                except Exception:
                    return jsonify({"message": "Invalid userId format"}), 400

            choice = bet.get("choice")
            if choice not in VALID_CHOICES:
                return jsonify({"message": "Invalid bet.choice", "allowed": list(VALID_CHOICES)}), 400

            try:
                stake = float(bet.get("stake", 0))
                odds  = float(bet.get("odds", 0))
            except Exception:
                return jsonify({"message": "Invalid stake/odds types"}), 400
            if stake <= 0: return jsonify({"message": "stake must be > 0"}), 400
            if odds  <= 1: return jsonify({"message": "odds must be >= 1"}), 400

            if choice == "winner":
                pick_team = _norm_name(bet.get("team"))
                if not pick_team:
                    return jsonify({"message": "For choice= 'winner' you must provide bet.team"}), 400

            if choice == "score":
                score = bet.get("score") or {}
                try:
                    s1 = int(score.get("team_1"))
                    s2 = int(score.get("team_2"))
                except Exception:
                    return jsonify({"message": "For choice='score' you must provide an integer score.team_1 and score.team_2"}), 400
                if s1 < 0 or s2 < 0:
                    return jsonify({"message": "score values must be >= 0"}), 400

            # Match lookup (Date + String)
            day_start_aware = datetime(event_dt.year, event_dt.month, event_dt.day, tzinfo=timezone.utc)
            day_end_aware   = day_start_aware + timedelta(days=1)
            day_start_nv = day_start_aware.replace(tzinfo=None)
            day_end_nv   = day_end_aware.replace(tzinfo=None)
            eq_date_str  = event_date_raw.strip() if isinstance(event_date_raw, str) else None

            match_query_or = [
                {"comand1.name": team_1, "comand2.name": team_2, "date": {"$gte": day_start_nv, "$lt": day_end_nv}},
                {"comand1.name": team_2, "comand2.name": team_1, "date": {"$gte": day_start_nv, "$lt": day_end_nv}},
            ]
            if eq_date_str and YYYY_MM_DD_RE.match(eq_date_str):
                match_query_or += [
                    {"comand1.name": team_1, "comand2.name": team_2, "date": eq_date_str},
                    {"comand1.name": team_2, "comand2.name": team_1, "date": eq_date_str},
                ]

            match_doc = MATCHES.find_one({"$or": match_query_or})
            if not match_doc:
                return jsonify({"message": "No such match has been found for given teams and date."}), 400

            # Duplicate (Date + String)
            dup_or = [
                {"event.team_1": team_1, "event.team_2": team_2},
                {"event.team_1": team_2, "event.team_2": team_1},
            ]
            dup_query_or = [{
                "userEmail": user_email,
                "bet.choice": choice,
                "$or": dup_or,
                "event.date": {"$gte": day_start_nv, "$lt": day_end_nv},
            }]
            if eq_date_str and YYYY_MM_DD_RE.match(eq_date_str):
                dup_query_or.append({
                    "userEmail": user_email,
                    "bet.choice": choice,
                    "$or": dup_or,
                    "event.date": eq_date_str,
                })
            duplicate = BETS.find_one({"$or": dup_query_or})
            if duplicate:
                return jsonify({"message": "Duplicate bet: you have already placed this type of bet for these teams on this date."}), 400

            stored_event_date = _storage_date(event_date_raw, event_dt)

            doc = {
                "userEmail": user_email,
                "userId": user_id,
                "event": {
                    "team_1": team_1,
                    "team_2": team_2,
                    "type": (event.get("type") or "").strip(),
                    "date": stored_event_date,
                },
                "bet": { **bet, "odds": float(odds), "stake": float(stake) },
                "status": "pending",
                "createdAt": datetime.utcnow(),
            }

            res = BETS.insert_one(doc)
            new_bet = BETS.find_one({"_id": res.inserted_id})
            return jsonify({"message": "Bet added successfully.", "bet": ser(new_bet)}), 201

        except Exception as e:
            return jsonify({"message": "Failed to add bet.", "error": str(e)}), 400

    # ---------- DELETE ----------
    @app.delete("/bets/<id>")
    def delete_bet(id):
        oid = to_oid(id)
        if not oid:
            return jsonify({"error": "Invalid id"}), 400
        res = BETS.delete_one({"_id": oid})
        if not res.deleted_count:
            return jsonify({"error": "Not found"}), 404
        return jsonify({"deleted": True, "_id": id})

    # ---------- SUMMARY ----------
    @app.get("/bets/summary")
    def bet_summary():
        summary = {}
        for b in BETS.find({}):
            email = b.get("userEmail")
            stake = to_float(b.get("bet", {}).get("stake", 0))
            odds  = to_float(b.get("bet", {}).get("odds", 1))
            amount = Decimal(str(stake * odds))
            if not email:
                continue
            if email not in summary:
                summary[email] = {"total_won": Decimal("0"), "total_lost": Decimal("0")}
            if b.get("status") == "won":
                summary[email]["total_won"]  += amount
            elif b.get("status") == "lost":
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
        return Response(json.dumps(output), mimetype="application/json")

    # ---------- UPDATE STATUS ----------
    @app.post("/bets/update_status")
    def update_bet_status():
        data = request.get_json(silent=True) or {}
        bet_id = data.get("betId")
        status = data.get("status")
        if not bet_id or not status:
            return jsonify({"error": "Missing betId or status"}), 400
        oid = to_oid(bet_id)
        if not oid:
            return jsonify({"error": "Invalid betId"}), 400
        res = BETS.update_one({"_id": oid}, {"$set": {"status": status}})
        if res.modified_count == 0:
            return jsonify({"error": "No bet updated"}), 404
        return jsonify({"message": "Bet status updated", "betId": bet_id, "status": status})
