from flask import request, jsonify
from bson import ObjectId
from bson.decimal128 import Decimal128
from decimal import Decimal
from datetime import datetime
from collections import OrderedDict
import json
from flask import Response

def register_teams_routes(app, db):
    TEAMS = db.Team             # Collection

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

            # --- Insert new team if unique ----
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
        sport = request.args.get("sport")
        name = request.args.get("name")
        min_rating = request.args.get("min_rating", type=int)
        max_rating = request.args.get("max_rating", type=int)

        query = {}
        if sport:
            query["sport"] = sport
        if name:
            query["teamName"] = {"$regex": name, "$options": "i"}
        if min_rating is not None or max_rating is not None:
            rng = {}
            if min_rating is not None: rng["$gte"] = min_rating
            if max_rating is not None: rng["$lte"] = max_rating
            query["rating"] = rng

        total = TEAMS.count_documents(query)
        items = [ser(x) for x in TEAMS.find(query)]
        return jsonify({"items": items, "total": total})

    # REORDER
    @app.get("/teams/reorder")
    def reorder_teams():
        """Sort teams by given field"""
        sort_by = request.args.get("sort_by", "rating")
        ascending = request.args.get("ascending", "true").lower() == "true"
        order = 1 if ascending else -1
        cur = TEAMS.find({}).sort(sort_by, order)
        return jsonify([ser(x) for x in cur])

#--------------- AGREGATIONS ---------------------------------
    @app.get("/teams/aggregations/football_stats")
    def football_team_stats():
        """
        Aggregation: total goals scored/conceded, yellow/red cards for football teams.
        Works with fields: $team1.name / $team2.name / result.*
        """
        pipeline = [
            {"$match": {"sport": "football"}},                  #paimamos tik komandos su sporto šaka 'football'

            {"$lookup": {                                       # Prijungiame iš 'Matches' kolekcijos rungtynes pagal komandos pavadinimą
                "from": "Matches",                              # Iš kokios kolekcijos traukti duomenis – 'Matches'
                "let": {"team_name": "$teamName"},              # 'let' apibrėžia vietinį kintamąjį su šios komandos pavadinimu
                "pipeline": [
                    {"$match": {
                        "$expr": {                              # $expr, kad galėtume lyginti laukus ir kintamuosius.
                            "$and": [                           # Imame tik tas rungtynes, kurios taip pat 'football'.
                                {"$eq": ["$sport", "football"]},
                                {"$or": [
                                    {"$regexMatch": {"input": "$team1.name", "regex": "$$team_name", "options": "i"}},
                                    {"$regexMatch": {"input": "$team2.name", "regex": "$$team_name", "options": "i"}}
                                ]}
                            ]
                        }
                    }}
                ],
                "as": "matches"                                 # Suderinamos rungtynės atsiduria masyve 'matches'.
            }},

            {"$unwind": {"path": "$matches", "preserveNullAndEmptyArrays": False}},

            {"$project": {
                "teamName": 1,
                "sport": 1,
                "scored": {                                     #   komandos įvarčiai rungtynėse
                    "$cond": [                                  #    Jei ši komanda buvo '$team1', imame '$team1.result.goalsFor' kitaip 2 komandai
                        {"$regexMatch": {"input": "$matches.$team1.name", "regex": "$teamName", "options": "i"}},
                        "$matches.$team1.result.goalsFor",
                        "$matches.team2.result.goalsFor"
                    ]
                },
                "conceded": {                                    #    Praleisti įvarčiai analogiškai (goalsAgainst):
                    "$cond": [
                        {"$regexMatch": {"input": "$matches.$team1.name", "regex": "$teamName", "options": "i"}},
                        "$matches.$team1.result.goalsAgainst",
                        "$matches.team2.result.goalsAgainst"
                    ]
                },
                "yellow": {
                    "$cond": [
                        {"$regexMatch": {"input": "$matches.$team1.name", "regex": "$teamName", "options": "i"}},
                        "$matches.$team1.result.cards.yellow",
                        "$matches.team2.result.cards.yellow"
                    ]
                },
                "red": {
                    "$cond": [
                        {"$regexMatch": {"input": "$matches.$team1.name", "regex": "$teamName", "options": "i"}},
                        "$matches.$team1.result.cards.red",
                        "$matches.team2.result.cards.red"
                    ]
                }
            }},

            {"$group": {                                        # sugrupuojame pagal komandos pavadinimą
                "_id": "$teamName",
                "total_scored": {"$sum": "$scored"},
                "total_conceded": {"$sum": "$conceded"},
                "yellow_cards": {"$sum": "$yellow"},
                "red_cards": {"$sum": "$red"}
            }},

            {"$project": {                                      # Galutinis formavimas:
                "_id": 0,
                "teamName": "$_id",
                "total_scored": 1,
                "total_conceded": 1,
                "goal_diff": {"$subtract": ["$total_scored", "$total_conceded"]}, # Įvarčių skirtumas = įmušti - praleisti.
                "yellow_cards": 1,
                "red_cards": 1
            }}
        ]

        result = list(db.Team.aggregate(pipeline))              # Paleidžiame agregaciją 'Team' kolekcijoje ir paverčiame į sąrašą.
        return jsonify(result)                                  # Grąžiname JSON atsakymą.


    @app.get("/teams/aggregations/basketball_stats")
    def basketball_team_stats():
        """
        Aggregation: average fouls per match, total scored/conceded points, and score difference.
        Works with basketball matches (sport='basketball').
        """
        pipeline = [
            {"$match": {"sport": "basketball"}},

            {"$lookup": {
                "from": "Matches",
                "let": {"team_name": "$teamName"},
                "pipeline": [
                    {"$match": {
                        "$expr": {
                            "$and": [
                                {"$eq": ["$sport", "basketball"]},
                                {"$or": [
                                    {"$regexMatch": {"input": "$team1.name", "regex": "$$team_name", "options": "i"}},
                                    {"$regexMatch": {"input": "$team2.name", "regex": "$$team_name", "options": "i"}}
                                ]}
                            ]
                        }
                    }}
                ],
                "as": "matches"
            }},

            {"$unwind": {"path": "$matches", "preserveNullAndEmptyArrays": False}},

            {"$project": {
                "teamName": 1,
                "scored_points": {
                    "$cond": [
                        {"$regexMatch": {"input": "$matches.$team1.name", "regex": "$teamName", "options": "i"}},
                        {"$add": [
                            "$matches.$team1.result.pointsBreakdown.one",
                            {"$multiply": [2, "$matches.$team1.result.pointsBreakdown.two"]},
                            {"$multiply": [3, "$matches.$team1.result.pointsBreakdown.three"]}
                        ]},
                        {"$add": [
                            "$matches.team2.result.pointsBreakdown.one",
                            {"$multiply": [2, "$matches.team2.result.pointsBreakdown.two"]},
                            {"$multiply": [3, "$matches.team2.result.pointsBreakdown.three"]}
                        ]}
                    ]
                },
                "conceded_points": {
                    "$cond": [
                        {"$regexMatch": {"input": "$matches.$team1.name", "regex": "$teamName", "options": "i"}},
                        {"$add": [
                            "$matches.team2.result.pointsBreakdown.one",
                            {"$multiply": [2, "$matches.team2.result.pointsBreakdown.two"]},
                            {"$multiply": [3, "$matches.team2.result.pointsBreakdown.three"]}
                        ]},
                        {"$add": [
                            "$matches.$team1.result.pointsBreakdown.one",
                            {"$multiply": [2, "$matches.$team1.result.pointsBreakdown.two"]},
                            {"$multiply": [3, "$matches.$team1.result.pointsBreakdown.three"]}
                        ]}
                    ]
                },
                "fouls": {
                    "$cond": [
                        {"$regexMatch": {"input": "$matches.$team1.name", "regex": "$teamName", "options": "i"}},
                        "$matches.$team1.result.fouls",
                        "$matches.team2.result.fouls"
                    ]
                }
            }},

            {"$group": {
                "_id": "$teamName",
                "total_scored": {"$sum": "$scored_points"},
                "total_conceded": {"$sum": "$conceded_points"},
                "total_fouls": {"$sum": "$fouls"},
                "match_count": {"$sum": 1}
            }},

            {"$project": {
                "_id": 0,
                "teamName": "$_id",
                "total_scored": 1,
                "total_conceded": 1,
                "goal_diff": {"$subtract": ["$total_scored", "$total_conceded"]},
                "avg_fouls": {
                    "$cond": [
                        {"$gt": ["$match_count", 0]},
                        {"$divide": ["$total_fouls", "$match_count"]},
                        0
                    ]
                },
                "match_count": 1
            }}
        ]

        result = list(db.Team.aggregate(pipeline))
        return jsonify(result)



