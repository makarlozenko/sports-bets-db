from flask import jsonify
from neo4j_connect import driver

#Checking bets relationships by user
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
        return jsonify({"user": email, "bets": bets})