from flask import request, jsonify, current_app
from neo4j_connect import driver

# ============================================================
# 1. USER BETS
# ============================================================
def register_neo4j_routes(app):
    @app.route("/neo4j/by_user/<email>/bets", methods=["GET"])
    def get_user_bets(email):

        with driver.session(database="neo4j") as session:
            result = session.run(
                """
                MATCH (u:User {id: $email})-[:PLACED]->(b:Bet)
                OPTIONAL MATCH (b)-[:ON_MATCH]->(m:Match)
                OPTIONAL MATCH (b)-[:ON_TEAM]->(t:Team)
                RETURN u.id AS user, b.id AS bet_id, 
                       m.id AS match_id, m.sport AS match_sport,
                       t.id AS team_id, t.name AS team_name
                """,
                {"email": email}
            )
            bets = [record.data() for record in result]

        return jsonify({"user": email, "bets": bets}), 200


# ============================================================
# 2. RIVALRIES
# ============================================================
def register_neo4j_rivalry_routes(app):

    @app.post("/neo4j/rivalry")
    def create_rivalry():
        data = request.get_json(silent=True) or {}
        t1 = data.get("team1")
        t2 = data.get("team2")

        if not t1 or not t2:
            return jsonify({"error": "team1 and team2 are required"}), 400

        if t1 == t2:
            return jsonify({"error": "A team cannot be rival with itself"}), 400

        # Use MongoDB via app.db
        mongo = current_app.db

        team1_exists = mongo.Team.find_one({"teamName": t1})
        team2_exists = mongo.Team.find_one({"teamName": t2})

        missing = []
        if not team1_exists:
            missing.append(t1)
        if not team2_exists:
            missing.append(t2)

        if missing:
            return jsonify({
                "error": "Some teams do not exist in MongoDB",
                "missing_teams": missing
            }), 404

        query_check = """
        MATCH (a:Team {name: $t1})-[r:RIVAL_OF]-(b:Team {name: $t2})
        RETURN r
        """

        with driver.session(database="neo4j") as session:
            exists = session.run(query_check, t1=t1, t2=t2).single()

        if exists:
            return jsonify({
                "message": "These teams are already rivals",
                "team1": t1,
                "team2": t2
            }), 200

        query = """
        MERGE (a:Team {name: $t1})
        MERGE (b:Team {name: $t2})
        MERGE (a)-[:RIVAL_OF]-(b)
        RETURN a.name AS team1, b.name AS team2
        """

        with driver.session(database="neo4j") as session:
            record = session.run(query, t1=t1, t2=t2).single()

        return jsonify({
            "message": "RIVAL_OF relationship created",
            "team1": record["team1"],
            "team2": record["team2"]
        }), 201

    @app.get("/neo4j/team/<team>/rivals")
    def deep_rivals(team):

        mongo = current_app.db
        team_exists = mongo.Team.find_one({"teamName": team})

        if not team_exists:
            return jsonify({
                "error": "Team does not exist in MongoDB",
                "team": team
            }), 404

        query = """
        MATCH (start:Team {name: $team})
        MATCH path = (start)-[:RIVAL_OF*1..10]-(other:Team)
        WHERE other.name <> $team
        RETURN DISTINCT other.name AS rival, length(path) AS distance
        ORDER BY distance ASC
        """

        with driver.session(database="neo4j") as session:
            result = session.run(query, team=team)
            rivals = [
                {"team": r["rival"], "distance": r["distance"]}
                for r in result
            ]

        return jsonify({
            "team": team,
            "total_rivals": len(rivals),
            "rivals": rivals
        }), 200
    @app.delete("/neo4j/rivalry")
    def delete_rivalry():
        data = request.get_json(silent=True) or {}
        t1 = data.get("team1")
        t2 = data.get("team2")

        if not t1 or not t2:
            return jsonify({"error": "team1 and team2 are required"}), 400

        if t1 == t2:
            return jsonify({"error": "Same team cannot be used twice"}), 400

        query = """
        MATCH (a:Team {name: $t1})
        MATCH (b:Team {name: $t2})
        MATCH (a)-[r:RIVAL_OF]-(b)
        DELETE r
        RETURN count(r) AS removed
        """

        with driver.session(database="neo4j") as session:
            removed = session.run(query, t1=t1, t2=t2).single()["removed"]

        if removed == 0:
            return jsonify({
                "message": "No rivalry existed between these teams"
            }), 404

        return jsonify({
            "message": "RIVAL_OF relationship deleted",
            "team1": t1,
            "team2": t2
        }), 200
    @app.delete("/neo4j/rivalries/all")
    def delete_all_rivalries():
        query = "MATCH ()-[r:RIVAL_OF]-() DELETE r RETURN count(r) AS removed"

        with driver.session(database="neo4j") as session:
            removed = session.run(query).single()["removed"]

        return jsonify({
            "message": "All rivalry relationships deleted",
            "deleted_count": removed
        }), 200
