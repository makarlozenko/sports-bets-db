from flask import request, jsonify
from bson import ObjectId
from bson.decimal128 import Decimal128
from decimal import Decimal
from datetime import datetime
from collections import OrderedDict
import json
from flask import Response

from RedisApp import cache_get_json, cache_set_json, invalidate, invalidate_pattern
from neo4j_connect import driver as neo4j_driver

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

    def sync_team_to_neo4j(team_doc):
        team_name = team_doc.get("teamName")
        sport = team_doc.get("sport")
        if not team_name:
            return
        with neo4j_driver.session(database="neo4j") as session:
            session.run("""
                MERGE (t:Team {name: $name})
                SET t.sport = $sport
            """, {"name": team_name, "sport": sport})

    @app.get("/health")
    def health():
        return jsonify({"ok": True, "db": "SportBET", "collections": db.list_collection_names()})
    # LIST
    @app.get("/teams")
    def list_teams():
        cache_key = "teams:list"
        cached = cache_get_json(cache_key)
        if cached:
            return jsonify(cached), 200

        cur = TEAMS.find({})
        items = [ser(x) for x in cur]
        total = TEAMS.count_documents({})
        result = {"items": items, "total": total}

        cache_set_json(cache_key, result, ttl=45)
        return jsonify(result)

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

            invalidate_pattern("teams:list:*")
            invalidate_pattern("teams:aggregations:*")
            invalidate_pattern("teams:filter:*")
            invalidate_pattern("teams:reorder:*")

            try:
                sync_team_to_neo4j(new_team)
            except Exception as e:
                print("Failed to sync team to Neo4j:", e)

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

        invalidate_pattern("teams:list:*")
        invalidate_pattern("teams:aggregations:*")
        invalidate_pattern("teams:filter:*")
        invalidate_pattern("teams:reorder:*")

        return jsonify(ser(TEAMS.find_one({"_id": oid}))), 200

    # DELETE
    @app.delete("/teams/<id>")
    def delete_team(id):
        oid = to_oid(id)
        if not oid:
            return jsonify({"error": "Invalid id"}), 400
        res = TEAMS.delete_one({"_id": oid})
        if not res.deleted_count:
            return jsonify({"error": "Not found"}), 404

        invalidate_pattern("teams:list:*")
        invalidate_pattern("teams:aggregations:*")
        invalidate_pattern("teams:filter:*")
        invalidate_pattern("teams:reorder:*")

        return jsonify({"deleted": True, "_id": id}), 200


    # FILTER
    @app.get("/teams/filter")
    def filter_teams():
        sport = request.args.get("sport")
        name = request.args.get("name")
        min_rating = request.args.get("min_rating", type=int)
        max_rating = request.args.get("max_rating", type=int)

        cache_key = f"teams:filter:{sport}:{name}:{min_rating}:{max_rating}"
        cached = cache_get_json(cache_key)
        if cached:
            return jsonify(cached)

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
        data = {"items": items, "total": total}

        cache_set_json(cache_key, data, ttl=45)
        return jsonify(data)

    # REORDER
    @app.get("/teams/reorder")
    def reorder_teams():
        """Sort teams by given field"""
        sort_by = request.args.get("sort_by", "rating")
        ascending = request.args.get("ascending", "true").lower() == "true"
        order = 1 if ascending else -1

        cache_key = f"teams:reorder:{sort_by}:{ascending}"
        cached = cache_get_json(cache_key)
        if cached:
            return jsonify(cached), 200

        cur = TEAMS.find({}).sort(sort_by, order)
        items = [ser(x) for x in cur]
        data = {"items": items, "sort_by": sort_by, "ascending": ascending}

        cache_set_json(cache_key, data, ttl=45)
        return jsonify(data), 200

#--------------- AGREGATIONS ---------------------------------
    @app.get("/teams/aggregations/football_stats")
    def football_team_stats():
        """
        Aggregation: total goals scored/conceded, yellow/red cards for football teams.
        Works with fields: $team1.name / $team2.name / result.*
        """
        cache_key = "teams:aggregations:football_stats"
        cached = cache_get_json(cache_key)
        if cached:
            return jsonify(cached), 200

        pipeline = [
            # 1) Imame visas "football" komandas (case-insensitive tikslus atitikmuo)
            {"$match": {"sport": {"$regex": "^football$", "$options": "i"}}},

            # 2) Surišame jų rungtynes
            {"$lookup": {
                "from": "Matches",
                "let": {"team_name": "$teamName"},
                "pipeline": [
                    {"$match": {
                        "$expr": {
                            "$and": [
                                {"$eq": ["$sport", "football"]},
                                {"$or": [
                                    # tiksli, bet case-insensitive lygybė (be regex spąstų)
                                    {"$eq": [{"$toLower": "$team1.name"}, {"$toLower": "$$team_name"}]},
                                    {"$eq": [{"$toLower": "$team2.name"}, {"$toLower": "$$team_name"}]}
                                ]}
                            ]
                        }
                    }}
                ],
                "as": "matches"
            }},

            # 3) Neišmetam komandų be rungtynių
            {"$unwind": {"path": "$matches", "preserveNullAndEmptyArrays": True}},

            # 4) Išsitraukiam saugius laukus su $ifNull
            {"$set": {
                "t1_goals_for": {"$ifNull": ["$matches.team1.result.goalsFor", 0]},
                "t1_goals_against": {"$ifNull": ["$matches.team1.result.goalsAgainst", 0]},
                "t2_goals_for": {"$ifNull": ["$matches.team2.result.goalsFor", 0]},
                "t2_goals_against": {"$ifNull": ["$matches.team2.result.goalsAgainst", 0]},
                "t1_y": {"$ifNull": ["$matches.team1.result.cards.yellow", 0]},
                "t1_r": {"$ifNull": ["$matches.team1.result.cards.red", 0]},
                "t2_y": {"$ifNull": ["$matches.team2.result.cards.yellow", 0]},
                "t2_r": {"$ifNull": ["$matches.team2.result.cards.red", 0]},

                "is_t1": {
                    "$cond": [
                        {"$gt": [{"$type": "$matches"}, "missing"]},  # jei matches neegzistuoja -> false
                        {"$eq": [{"$toLower": "$matches.team1.name"}, {"$toLower": "$teamName"}]},
                        False
                    ]
                }
            }},

            # 5) Paverčiam į vienos rungtynės indėlį, 0 jei rungtynių nėra
            {"$project": {
                "teamName": 1,
                "scored": {"$cond": ["$is_t1", "$t1_goals_for", "$t2_goals_for"]},
                "conceded": {"$cond": ["$is_t1", "$t1_goals_against", "$t2_goals_against"]},
                "yellow": {"$cond": ["$is_t1", "$t1_y", "$t2_y"]},
                "red": {"$cond": ["$is_t1", "$t1_r", "$t2_r"]}
            }},

            # 6) Sumos per komandą (komandos be rungtynių turės 0 sumas)
            {"$group": {
                "_id": "$teamName",
                "total_scored": {"$sum": "$scored"},
                "total_conceded": {"$sum": "$conceded"},
                "yellow_cards": {"$sum": "$yellow"},
                "red_cards": {"$sum": "$red"}
            }},

            {"$project": {
                "_id": 0,
                "teamName": "$_id",
                "total_scored": 1,
                "total_conceded": 1,
                "goal_diff": {"$subtract": ["$total_scored", "$total_conceded"]},
                "yellow_cards": 1,
                "red_cards": 1
            }}
        ]

        result = list(db.Team.aggregate(pipeline))
        cache_set_json(cache_key, result, ttl=45)
        return jsonify(result), 200


    @app.get("/teams/aggregations/basketball_stats")
    def basketball_team_stats():
        """
        Aggregation: average fouls per match, total scored/conceded points, and score difference.
        Works with basketball matches (sport='basketball').
        """
        cache_key = "teams:aggregations:basketball_stats"
        cached = cache_get_json(cache_key)
        if cached:
            return jsonify(cached), 200

        pipeline = [
            # 1) visos krepšinio komandos (case-insensitive tikslus atitikmuo)
            {"$match": {"sport": {"$regex": "^basketball$", "$options": "i"}}},

            # 2) prisijungiame atitinkamas rungtynes
            {"$lookup": {
                "from": "Matches",
                "let": {"team_name": "$teamName"},
                "pipeline": [
                    {"$match": {
                        "$expr": {
                            "$and": [
                                {"$eq": ["$sport", "basketball"]},
                                {"$or": [
                                    {"$eq": [{"$toLower": "$team1.name"}, {"$toLower": "$$team_name"}]},
                                    {"$eq": [{"$toLower": "$team2.name"}, {"$toLower": "$$team_name"}]}
                                ]}
                            ]
                        }
                    }}
                ],
                "as": "matches"
            }},

            # 3) neišmetam komandų be rungtynių
            {"$unwind": {"path": "$matches", "preserveNullAndEmptyArrays": True}},

            # 4) saugūs laukai + indikatorius ar ši komanda buvo team1
            {"$set": {
                "t1_one": {"$ifNull": ["$matches.team1.result.pointsBreakdown.one", 0]},
                "t1_two": {"$ifNull": ["$matches.team1.result.pointsBreakdown.two", 0]},
                "t1_three": {"$ifNull": ["$matches.team1.result.pointsBreakdown.three", 0]},
                "t2_one": {"$ifNull": ["$matches.team2.result.pointsBreakdown.one", 0]},
                "t2_two": {"$ifNull": ["$matches.team2.result.pointsBreakdown.two", 0]},
                "t2_three": {"$ifNull": ["$matches.team2.result.pointsBreakdown.three", 0]},
                "t1_fouls": {"$ifNull": ["$matches.team1.result.fouls", 0]},
                "t2_fouls": {"$ifNull": ["$matches.team2.result.fouls", 0]},
                "t1name": {"$ifNull": ["$matches.team1.name", ""]},
                "t2name": {"$ifNull": ["$matches.team2.name", ""]},
                "is_t1": {
                    "$cond": [
                        {"$gt": [{"$type": "$matches"}, "missing"]},
                        {"$eq": [{"$toLower": "$matches.team1.name"}, {"$toLower": "$teamName"}]},
                        False
                    ]
                }
            }},

            # 5) vienų rungtynių indėlis (0 jei rungtynių nėra)
            {"$set": {
                "scored_points": {
                    "$cond": [
                        "$is_t1",
                        {"$add": ["$t1_one", {"$multiply": [2, "$t1_two"]}, {"$multiply": [3, "$t1_three"]}]},
                        {"$add": ["$t2_one", {"$multiply": [2, "$t2_two"]}, {"$multiply": [3, "$t2_three"]}]}
                    ]
                },
                "conceded_points": {
                    "$cond": [
                        "$is_t1",
                        {"$add": ["$t2_one", {"$multiply": [2, "$t2_two"]}, {"$multiply": [3, "$t2_three"]}]},
                        {"$add": ["$t1_one", {"$multiply": [2, "$t1_two"]}, {"$multiply": [3, "$t1_three"]}]}
                    ]
                },
                "fouls": {"$cond": ["$is_t1", "$t1_fouls", "$t2_fouls"]},

                # skaičiuosim match_count tik kai yra bent vienas pavadinimas (t. y. tikros rungtynės)
                "has_match": {"$or": [{"$ne": ["$t1name", ""]}, {"$ne": ["$t2name", ""]}]}
            }},

            # 6) sumos per komandą
            {"$group": {
                "_id": "$teamName",
                "total_scored": {"$sum": "$scored_points"},
                "total_conceded": {"$sum": "$conceded_points"},
                "total_fouls": {"$sum": "$fouls"},
                "match_count": {"$sum": {"$cond": ["$has_match", 1, 0]}}
            }},

            # 7) galutinis vaizdas + vidurkis
            {
                "$project": {
                    "_id": 0,
                    "teamName": "$_id",
                    "total_scored": 1,
                    "total_conceded": 1,
                    "goal_diff": {"$subtract": ["$total_scored", "$total_conceded"]},
                    "avg_fouls": {
                        "$cond": [
                            {"$gt": ["$match_count", 0]},
                            {"$round": [{"$divide": ["$total_fouls", "$match_count"]}, 2]},
                            0
                        ]
                    },
                    "match_count": 1
                }
            }

        ]

        result = list(db.Team.aggregate(pipeline))
        cache_set_json(cache_key, result, ttl=45)
        return jsonify(result), 200




