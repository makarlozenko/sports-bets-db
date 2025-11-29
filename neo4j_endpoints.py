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

    # ============================================================
    # 3. RECOMMENDATIONS & SIMILAR USERS
    # ============================================================
def register_neo4j_recommendation_routes(app):

        # ---------- /neo4j/user/<email>/similar ----------
        @app.get("/neo4j/user/<email>/similar")
        def similar_users(email):
            """
            Find users who bet on the same matches or teams as the given user.
            Similarity score = 2 * commonMatches + commonTeams
            """
            query = """
            MATCH (u:User {id: $email})
            //rungtynės ir komandos ant kurių statė useris
            OPTIONAL MATCH (u)-[:PLACED]->(b:Bet)
            OPTIONAL MATCH (b)-[:ON_MATCH]->(m:Match)
            OPTIONAL MATCH (b)-[:ON_TEAM]->(t:Team)
            WITH u,
                 collect(DISTINCT m) AS myMatches,
                 collect(DISTINCT t) AS myTeams

            //kiti useriai ir jų statymai
            MATCH (other:User)
            WHERE other <> u
            OPTIONAL MATCH (other)-[:PLACED]->(b2:Bet)
            OPTIONAL MATCH (b2)-[:ON_MATCH]->(m2:Match)
            OPTIONAL MATCH (b2)-[:ON_TEAM]->(t2:Team)
            WITH u, other, myMatches, myTeams,
                 collect(DISTINCT m2) AS otherMatches,
                 collect(DISTINCT t2) AS otherTeams

            WITH other,
                 [m IN otherMatches WHERE m IN myMatches] AS commonMatches,
                 [t IN otherTeams   WHERE t IN myTeams]   AS commonTeams
            WITH other,
                 size(commonMatches) AS commonMatchCount,
                 size(commonTeams)   AS commonTeamCount
            WHERE commonMatchCount > 0 OR commonTeamCount > 0

            RETURN other.id AS user,
                   commonMatchCount AS commonMatches,
                   commonTeamCount AS commonTeams,
                   2 * commonMatchCount + commonTeamCount AS score
            ORDER BY score DESC
            LIMIT 10
            """

            with driver.session(database="neo4j") as session:
                result = session.run(query, email=email)
                users = [record.data() for record in result]

            return jsonify({
                "user": email,
                "similar_users": users,
            }), 200

        # ---------- /neo4j/recommend/matches/<email> ----------
        @app.get("/neo4j/recommend/matches/<email>")
        def recommend_matches(email):
            """
            Recommend matches for a user:
            - take teams the user has bet ON_TEAM
            - walk through RIVAL_OF relationships (1..3 hops)
            - find upcoming/scheduled matches of those rival teams
            """
            query = """
            MATCH (u:User {id: $email})-[:PLACED]->(b:Bet)-[:ON_TEAM]->(myTeam:Team)

            //gylusis apėjimas: RIVAL_OF*1..
            MATCH path = (myTeam)-[:RIVAL_OF*1..]-(rival:Team)

            WITH u, myTeam, rival, min(length(path)) AS distance
            //priešų rungtynės
            MATCH (m:Match)-[:HOME_TEAM|:AWAY_TEAM]->(rival)
            WHERE m.status IS NULL OR m.status IN ['SCHEDULED', 'OPEN']

            RETURN DISTINCT
                   rival.name AS rivalTeam,
                   collect(DISTINCT m.id)   AS matchIds,
                   collect(DISTINCT m.sport) AS sports,
                   distance
            ORDER BY distance ASC, size(matchIds) DESC
            LIMIT 20
            """

            with driver.session(database="neo4j") as session:
                result = session.run(query, email=email)
                recs = []
                for r in result:
                    recs.append({
                        "rivalTeam": r["rivalTeam"],
                        "distance": r["distance"],
                        "matchIds": r["matchIds"],
                        "sports": r["sports"],
                    })

            return jsonify({
                "user": email,
                "recommendations": recs
            }), 200
