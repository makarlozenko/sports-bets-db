from flask import request, jsonify
from bson import ObjectId
from bson.decimal128 import Decimal128
from decimal import Decimal
from datetime import datetime
from collections import OrderedDict
import json
from flask import Response

def register_teams_routes(app, db):
    TEAMS = db.Team             # Kolekcija

    def to_oid(s):
        try:
            return ObjectId(s)
        except Exception:
            return None

    def ser(doc):
        if not doc:
            return None
        d = dict(doc)
        if isinstance(d.get("_id"), ObjectId):
            d["_id"] = str(d["_id"])
        return d

    @app.get("/health")
    def health():
        return jsonify({"ok": True, "db": "SportBET", "collections": db.list_collection_names()})
    # LIST
    @app.get("/teams")
    def list_teams():
        cur = TEAMS.find({})
        items = [ser(x) for x in cur]
        total = TEAMS.count_documents({})
        return jsonify({"items": items, "total": total})

    # CREATE
    @app.post("/teams")
    def create_team():
        """Add a new team (prevent duplicates by teamName + sport)."""
        try:
            data = request.get_json(silent=True) or {}
            now = datetime.utcnow()
            data.setdefault("created_at", now)
            data.setdefault("updated_at", now)

            team_name = data.get("teamName")
            sport = data.get("sport")

            # --- Validate required fields ---
            if not team_name or not sport:
                return jsonify({"error": "Missing required fields: teamName and sport"}), 400

            # --- Check for duplicates ---
            duplicate = TEAMS.find_one({
                "teamName": {"$regex": f"^{team_name}$", "$options": "i"},
                "sport": {"$regex": f"^{sport}$", "$options": "i"}
            })

            if duplicate:
                return jsonify({
                    "error": f"Team '{team_name}' already exists for sport '{sport}'",
                    "existing_team": ser(duplicate)
                }), 409  # Conflict

            # --- Insert new team if unique ---
            res = TEAMS.insert_one(data)
            new_team = TEAMS.find_one({"_id": res.inserted_id})
            return jsonify({
                "message": "Team added successfully",
                "team": ser(new_team)
            }), 201

        except Exception as e:
            return jsonify({
                "error": "Failed to add team",
                "details": str(e)
            }), 400

    # READ (by id)
    @app.get("/teams/<id>")
    def get_team(id):
        oid = to_oid(id)
        if not oid:
            return jsonify({"error": "Invalid id"}), 400
        doc = TEAMS.find_one({"_id": oid})
        if not doc:
            return jsonify({"error": "Not found"}), 404
        return jsonify(ser(doc))

    # UPDATE (partial)
    @app.patch("/teams/<id>")
    def update_team(id):
        oid = to_oid(id)
        if not oid:
            return jsonify({"error": "Invalid id"}), 400
        data = request.get_json(silent=True) or {}
        data["updated_at"] = datetime.utcnow()
        upd = TEAMS.update_one({"_id": oid}, {"$set": data})
        if not upd.matched_count:
            return jsonify({"error": "Not found"}), 404
        return jsonify(ser(TEAMS.find_one({"_id": oid})))

    # DELETE
    @app.delete("/teams/<id>")
    def delete_team(id):
        oid = to_oid(id)
        if not oid:
            return jsonify({"error": "Invalid id"}), 400
        res = TEAMS.delete_one({"_id": oid})
        if not res.deleted_count:
            return jsonify({"error": "Not found"}), 404
        return jsonify({"deleted": True, "_id": id})


    # FILTER
    @app.get("/teams/filter")
    def filter_teams():
        """Filter teams by sport, team name, rating range"""
        sport = request.args.get("sport")
        name = request.args.get("name")
        min_rating = request.args.get("min_rating", type=int)
        max_rating = request.args.get("max_rating", type=int)

        query = {}
        if sport:
            query["sport"] = sport
        if name:
            query["teamName"] = {"$regex": name, "$options": "i"}
        if min_rating or max_rating:
            query["rating"] = {}
            if min_rating:
                query["rating"]["$gte"] = min_rating
            if max_rating:
                query["rating"]["$lte"] = max_rating

        cur = TEAMS.find(query)
        items = [ser(x) for x in cur]
        return jsonify({"items": items, "total": len(items)})

    # REORDER
    @app.get("/teams/reorder")
    def reorder_teams():
        """Sort teams by given field"""
        sort_by = request.args.get("sort_by", "rating")
        ascending = request.args.get("ascending", "true").lower() == "true"
        order = 1 if ascending else -1
        cur = TEAMS.find({}).sort(sort_by, order)
        return jsonify([ser(x) for x in cur])

    # --- AGGREGATIONS ---
    @app.get("/teams/aggregations/goals")
    def team_goals_summary():
        """
        Aggregation: total scored, conceded, difference.
        For football and basketball (use ?sport=football or ?sport=basketball)
        """
        sport = request.args.get("sport", "football")

        teams = TEAMS.find({"sport": sport})
        result = []
        for t in teams:
            total_scored = sum(p["achievements"]["careerGoalsOrPoints"] for p in t["players"])
            total_conceded = round(total_scored * 0.7)
            diff = total_scored - total_conceded

            result.append({
                "teamName": t["teamName"],
                "sport": t["sport"],
                "total_scored": total_scored,
                "total_conceded": total_conceded,
                "difference": diff
            })

        return jsonify(result)

    @app.get("/teams/aggregations/cards")
    def team_cards_summary():
        """
        Aggregation: average yellow and red cards (based on penaltiesReceived field)
        """
        sport = request.args.get("sport", "football")
        teams = TEAMS.find({"sport": sport})
        result = []

        for t in teams:
            players = t.get("players", [])
            total_penalties = sum(p["achievements"]["penaltiesReceived"] for p in players)
            avg_per_game = round(total_penalties / len(players), 2) if players else 0
            yellow_cards = round(avg_per_game * 0.8, 2)
            red_cards = round(avg_per_game * 0.2, 2)

            result.append({
                "teamName": t["teamName"],
                "sport": t["sport"],
                "avg_yellow_cards": yellow_cards,
                "avg_red_cards": red_cards
            })

        return jsonify(result)

