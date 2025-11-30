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
                RETURN u.id  AS user,
                       b.id  AS bet_id,
                       m.id  AS match_id,
                       m.sport AS match_sport,
                       t.name AS team_name,
                       t.sport AS team_sport
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

        # Mongo DB
        mongo = current_app.db

        team1_doc = mongo.Team.find_one({"teamName": t1})
        team2_doc = mongo.Team.find_one({"teamName": t2})

        missing = []
        if not team1_doc:
            missing.append(t1)
        if not team2_doc:
            missing.append(t2)

        if missing:
            return jsonify({
                "error": "Some teams do not exist in MongoDB",
                "missing_teams": missing
            }), 404

        sport1 = team1_doc.get("sport")
        sport2 = team2_doc.get("sport")

        # jei sport skiriasi – nedarom rivalų
        if sport1 and sport2 and sport1 != sport2:
            return jsonify({
                "error": "Teams play different sports, cannot create rivalry",
                "team1": {"name": t1, "sport": sport1},
                "team2": {"name": t2, "sport": sport2},
            }), 400

        # pasirenkam sportą (jei viena komanda neturėjo, imsim iš kitos)
        sport = sport1 or sport2

        if not sport:
            return jsonify({
                "error": "Teams do not have sport set in MongoDB",
                "team1": t1,
                "team2": t2
            }), 400

        # Patikrinam, ar RIVAL_OF jau egzistuoja tame pačiame sporte
        query_check = """
        MATCH (a:Team {name: $t1, sport: $sport})-[r:RIVAL_OF]-
              (b:Team {name: $t2, sport: $sport})
        RETURN r
        """

        with driver.session(database="neo4j") as session:
            exists = session.run(query_check, t1=t1, t2=t2, sport=sport).single()

        if exists:
            return jsonify({
                "message": "These teams are already rivals",
                "team1": t1,
                "team2": t2,
                "sport": sport
            }), 200

        # Kuriam / užtikrinam Team node'us pagal tą pačią schemą kaip matches/bets
        query = """
        MERGE (a:Team {name: $t1, sport: $sport})
        MERGE (b:Team {name: $t2, sport: $sport})
        MERGE (a)-[:RIVAL_OF]-(b)
        RETURN a.name AS team1, b.name AS team2, a.sport AS sport
        """

        with driver.session(database="neo4j") as session:
            record = session.run(query, t1=t1, t2=t2, sport=sport).single()

        return jsonify({
            "message": "RIVAL_OF relationship created",
            "team1": record["team1"],
            "team2": record["team2"],
            "sport": record["sport"]
        }), 201

    @app.get("/neo4j/team/<team>/rivals")
    def deep_rivals(team):

        mongo = current_app.db
        team_doc = mongo.Team.find_one({"teamName": team})

        if not team_doc:
            return jsonify({
                "error": "Team does not exist in MongoDB",
                "team": team
            }), 404

        sport = team_doc.get("sport")
        if not sport:
            return jsonify({
                "error": "Team does not have sport set in MongoDB",
                "team": team
            }), 400

        query = """
        MATCH (start:Team {name: $team, sport: $sport})
        MATCH path = (start)-[:RIVAL_OF*1..10]-(other:Team)
        WHERE other.name <> $team
          AND other.sport = $sport
        RETURN DISTINCT other.name AS rival, length(path) AS distance
        ORDER BY distance ASC
        """

        with driver.session(database="neo4j") as session:
            result = session.run(query, team=team, sport=sport)
            rivals = [
                {"team": r["rival"], "distance": r["distance"]}
                for r in result
            ]

        return jsonify({
            "team": team,
            "sport": sport,
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

        # Mongo DB – pasiimam komandas ir jų sport
        mongo = current_app.db
        team1_doc = mongo.Team.find_one({"teamName": t1})
        team2_doc = mongo.Team.find_one({"teamName": t2})

        missing = []
        if not team1_doc:
            missing.append(t1)
        if not team2_doc:
            missing.append(t2)

        if missing:
            return jsonify({
                "error": "Some teams do not exist in MongoDB",
                "missing_teams": missing
            }), 404

        sport1 = team1_doc.get("sport")
        sport2 = team2_doc.get("sport")

        if sport1 and sport2 and sport1 != sport2:
            return jsonify({
                "error": "Teams play different sports, cannot delete rivalry between them",
                "team1": {"name": t1, "sport": sport1},
                "team2": {"name": t2, "sport": sport2},
            }), 400

        sport = sport1 or sport2
        if not sport:
            return jsonify({
                "error": "Teams do not have sport set in MongoDB",
                "team1": t1,
                "team2": t2
            }), 400

        query = """
        MATCH (a:Team {name: $t1, sport: $sport})
        MATCH (b:Team {name: $t2, sport: $sport})
        MATCH (a)-[r:RIVAL_OF]-(b)
        DELETE r
        RETURN count(r) AS removed
        """

        with driver.session(database="neo4j") as session:
            removed = session.run(query, t1=t1, t2=t2, sport=sport).single()["removed"]

        if removed == 0:
            return jsonify({
                "message": "No rivalry existed between these teams in this sport",
                "team1": t1,
                "team2": t2,
                "sport": sport
            }), 404

        return jsonify({
            "message": "RIVAL_OF relationship deleted",
            "team1": t1,
            "team2": t2,
            "sport": sport
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

        // rungtynės ir komandos, ant kurių statė šis useris
        OPTIONAL MATCH (u)-[:PLACED]->(b:Bet)
        OPTIONAL MATCH (b)-[:ON_MATCH]->(m:Match)
        OPTIONAL MATCH (b)-[:ON_TEAM]->(t:Team)
        WITH u,
             [x IN collect(DISTINCT m) WHERE x IS NOT NULL] AS myMatches,
             [x IN collect(DISTINCT t) WHERE x IS NOT NULL] AS myTeams

        // jei neturi jokiu statymų – nėra su kuo lyginti
        WHERE size(myMatches) > 0 OR size(myTeams) > 0

        // kiti useriai ir jų statymai
        MATCH (other:User)
        WHERE other <> u
        OPTIONAL MATCH (other)-[:PLACED]->(b2:Bet)
        OPTIONAL MATCH (b2)-[:ON_MATCH]->(m2:Match)
        OPTIONAL MATCH (b2)-[:ON_TEAM]->(t2:Team)
        WITH u, other, myMatches, myTeams,
             [x IN collect(DISTINCT m2) WHERE x IS NOT NULL] AS otherMatches,
             [x IN collect(DISTINCT t2) WHERE x IS NOT NULL] AS otherTeams

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
        Rekomenduoja match'us naudotojui:

        - bazinės komandos (baseTeams):
            * komandos, ant kurių jis statė (winner) -> (Bet)-[:ON_TEAM]->(Team)
            * komandos iš match'ų, ant kurių jis statė bet kokį bet ->
              (Bet)-[:ON_MATCH]->(Match)-[:HOME_TEAM|:AWAY_TEAM]->(Team)

        - iš baseTeams einame per RIVAL_OF*1.. (neapibrėžtas gylis) ir gauname ir rivals
        - surandame būsimus (SCHEDULED/OPEN) match'us šių komandų
        - atmetame match'us, ant kurių naudotojas jau statė
        - kiekvienas match grąžinamas tik kartą, su visomis jo komandomis
        """
        query = """
        // 1) surenkam bazines komandas susijusias su naudotojo statymais
        CALL {
            MATCH (u:User {id: $email})-[:PLACED]->(b:Bet)
            OPTIONAL MATCH (b)-[:ON_TEAM]->(t1:Team)
            OPTIONAL MATCH (b)-[:ON_MATCH]->(mBet:Match)
            OPTIONAL MATCH (mBet)-[:HOME_TEAM|:AWAY_TEAM]->(t2:Team)
            WITH
                collect(DISTINCT t1) + collect(DISTINCT t2) AS ts
            UNWIND [x IN ts WHERE x IS NOT NULL] AS t
            RETURN collect(DISTINCT t) AS baseTeams
        }

        // 2) iš baseTeams gauname kandidatines komandas:
        //    pačias baseTeams (distance=0) + jų rivals per RIVAL_OF*1.. (distance kelio ilgis)
        CALL {
            WITH baseTeams
            // mano komandos
            UNWIND baseTeams AS bt
            RETURN DISTINCT bt AS team, 0 AS distance

            UNION

            // rivals
            WITH baseTeams
            UNWIND baseTeams AS bt
            MATCH path = (bt)-[:RIVAL_OF*1..]-(rival:Team)
            WHERE rival.sport = bt.sport
            WITH rival, min(length(path)) AS dist
            RETURN DISTINCT rival AS team, dist AS distance
        }

        // 3) kandidatinių komandų match'ai
        MATCH (m:Match)-[:HOME_TEAM|:AWAY_TEAM]->(team)
        WHERE coalesce(m.status, 'SCHEDULED') IN ['SCHEDULED', 'OPEN']
          AND m.sport = team.sport

        // 4) match'ai, ant kurių naudotojas jau statė
        CALL {
            WITH $email AS email
            MATCH (u:User {id: email})-[:PLACED]->(:Bet)-[:ON_MATCH]->(mMy:Match)
            RETURN collect(DISTINCT mMy.id) AS myMatchIds
        }

        // 5) atmetam match'us ant kurių jau statyta
        WITH team, distance, m, myMatchIds
        WHERE NOT m.id IN myMatchIds

        // 6) sugrupuojam pagal match'ą, kad nebūtų dublikatų
        MATCH (m)-[:HOME_TEAM]->(home:Team)
        MATCH (m)-[:AWAY_TEAM]->(away:Team)

        WITH
            m,
            home,
            away,
            // minimalus atstumas tarp visų kandidatinių komandų susijusių su šiuo match'u
            min(distance) AS minDistance

        RETURN
            m.id            AS matchId,
            m.sport         AS sport,
            minDistance     AS distance,
            home.name       AS homeTeam,
            away.name       AS awayTeam
        ORDER BY distance ASC, matchId
        LIMIT 20
        """

        with driver.session(database="neo4j") as session:
            result = session.run(query, email=email)
            recs = []
            for r in result:
                recs.append({
                    "matchId": r["matchId"],
                    "sport": r["sport"],
                    "distance": r["distance"],  # 0 = tavo komanda; 1.. = per RIVAL_OF
                    "homeTeam": r["homeTeam"],
                    "awayTeam": r["awayTeam"],
                })

        return jsonify({
            "user": email,
            "recommendations": recs
        }), 200



