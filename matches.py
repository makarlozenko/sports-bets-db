from flask import request, jsonify
from bson import ObjectId
from datetime import datetime
from dateutil import parser
def register_matches_routes(app, db):
    MATCHES = db.Matches   # collection

    def to_oid(s):
        try:
            return ObjectId(s)
        except Exception:
            return None

    def parse_dt(s):
        try:
            return parser.isoparse(s)
        except Exception:
            return None

    def ser(doc):
        """Serialize MongoDB ObjectId and nested structures."""
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
        return d

    # ---------------------- CRUD ----------------------
    @app.get("/matches")
    def list_matches():
        sport = request.args.get("sport")
        date_from = parse_dt(request.args.get("from"))
        date_to = parse_dt(request.args.get("to"))

        sort_by = request.args.get("sort_by", "date")
        ascending = request.args.get("ascending", "false").lower() == "true"
        order = 1 if ascending else -1

        query = {}
        if sport:
            query["sport"] = sport
        if date_from or date_to:
            date_query = {}
            if date_from: date_query["$gte"] = date_from
            if date_to:   date_query["$lte"] = date_to
            query["date"] = date_query

        total = MATCHES.count_documents(query)
        cur = (MATCHES.find(query)
               .sort(sort_by, order))
        items = [ser(x) for x in cur]

        return jsonify({"items": items, "total": total})

    @app.get("/matches/<id>")
    def get_match(id):
        """Get match by ID."""
        oid = to_oid(id)
        if not oid:
            return jsonify({"error": "Invalid id"}), 400
        doc = MATCHES.find_one({"_id": oid})
        if not doc:
            return jsonify({"error": "Not found"}), 404
        return jsonify(ser(doc))

    @app.post("/matches")
    def create_match():
        """Add new match (prevent duplicates)."""
        try:
            data = request.get_json(silent=True) or {}
            now = datetime.utcnow()
            data.setdefault("created_at", now)
            data.setdefault("updated_at", now)

            # --- duplicate check ---
            sport = data.get("sport")
            match_type = data.get("matchType")
            date = data.get("date")
            team1 = data.get("team1", {}).get("name")
            team2 = data.get("team2", {}).get("name")

            if not all([sport, match_type, date, team1, team2]):
                return jsonify({"error": "Missing required match fields"}), 400

            duplicate = MATCHES.find_one({
                "sport": sport,
                "matchType": match_type,
                "date": date,
                "team1.name": team1,
                "team2.name": team2
            })

            if duplicate:
                return jsonify({
                    "error": "Duplicate match already exists for this date and teams",
                    "existing_match": ser(duplicate)
                }), 409

            # --- insert if unique ---
            res = MATCHES.insert_one(data)
            new_doc = MATCHES.find_one({"_id": res.inserted_id})
            return jsonify({"message": "Match added", "match": ser(new_doc)}), 201

        except Exception as e:
            return jsonify({"error": str(e)}), 400

    @app.patch("/matches/<id>")
    def update_match(id):
        """Update existing match."""
        oid = to_oid(id)
        if not oid:
            return jsonify({"error": "Invalid id"}), 400
        data = request.get_json(silent=True) or {}
        data["updated_at"] = datetime.utcnow()
        upd = MATCHES.update_one({"_id": oid}, {"$set": data})
        if not upd.matched_count:
            return jsonify({"error": "Not found"}), 404
        return jsonify(ser(MATCHES.find_one({"_id": oid})))

    @app.delete("/matches/<id>")
    def delete_match(id):
        """Delete match by ID."""
        oid = to_oid(id)
        if not oid:
            return jsonify({"error": "Invalid id"}), 400
        res = MATCHES.delete_one({"_id": oid})
        if not res.deleted_count:
            return jsonify({"error": "Not found"}), 404
        return jsonify({"deleted": True, "_id": id})

    # ---------------------- FILTER ----------------------

    @app.get("/matches/filter")
    def filter_matches():
        """
        Filter matches by sport, team name, or date range.
        Example: /matches/filter?sport=football&team=Vilnius&from=2025-09-01
        """
        sport = request.args.get("sport")
        team = request.args.get("team")
        date_from = request.args.get("from")
        date_to = request.args.get("to")

        query = {}
        if sport:
            query["sport"] = sport
        if team:
            query["$or"] = [
                {"team1.name": {"$regex": team, "$options": "i"}},
                {"team2.name": {"$regex": team, "$options": "i"}}
            ]
        if date_from or date_to:
            date_query = {}
            if date_from:
                date_query["$gte"] = date_from
            if date_to:
                date_query["$lte"] = date_to
            query["date"] = date_query

        cur = MATCHES.find(query)
        items = [ser(x) for x in cur]
        return jsonify({"items": items, "total": len(items)})

    # ---------------------- REORDER ----------------------
    @app.get("/matches/reorder")
    def reorder_matches():
        """
        Sort matches by date or sport.
        Example: /matches/reorder?sort_by=date&ascending=false
        """
        sort_by = request.args.get("sort_by", "date")
        ascending = request.args.get("ascending", "true").lower() == "true"
        order = 1 if ascending else -1

        cur = MATCHES.find({}).sort(sort_by, order)
        items = [ser(x) for x in cur]
        return jsonify(items)
