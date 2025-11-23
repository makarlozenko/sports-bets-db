from neo4j import GraphDatabase
from datetime import datetime
from flask import Flask, jsonify

# ---------- Neo4j driver setup ----------

URI = "neo4j+s://37b79b6d.databases.neo4j.io"
USER = "neo4j"
PASSWORD = "qCyhqY1TKvwPEKrzECH7N8u-jBJOkH2lkvXQFLQT8c8"

driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
def test_connection():
    """Simple sanity check used by CLI / debug."""
    with driver.session(database="neo4j") as session:
        result = session.run("RETURN 'Hello from Neo4j' AS msg")
        print(result.single()["msg"])


def seed_graph():
    """
    Create a small, feature-specific graph with fixed data:

      Users:  Arina, Edvinas
      Teams:  Vilnius Wolves, Kaunas Kings
      Match:  Wolves vs Kings
      Bets:   2 bets on that match
    """

    with driver.session(database="neo4j") as session:
        # ----- Schema / constraints -----
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (t:Team) REQUIRE t.id IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (m:Match) REQUIRE m.id IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (b:Bet) REQUIRE b.id IS UNIQUE")

        # ----- Teams -----
        session.run(
            """
            MERGE (t1:Team {id: 'team-vilnius-wolves'})
              ON CREATE SET t1.name = 'Vilnius Wolves',
                            t1.country = 'LT',
                            t1.sport = 'Basketball'
            """
        )

        session.run(
            """
            MERGE (t2:Team {id: 'team-kaunas-green'})
              ON CREATE SET t2.name = 'Kaunas Green',
                            t2.country = 'LT',
                            t2.sport = 'Basketball'
            """
        )

        # ----- Users -----
        session.run(
            """
            MERGE (u1:User {id: 'user-arina'})
              ON CREATE SET u1.name = 'Arina',
                            u1.country = 'LT',
                            u1.createdAt = datetime()
            """
        )

        session.run(
            """
            MERGE (u2:User {id: 'user-edvinas'})
              ON CREATE SET u2.name = 'Edvinas',
                            u2.country = 'LT',
                            u2.createdAt = datetime()
            """
        )

        # ----- Match -----
        session.run(
            """
            MATCH (home:Team {id: 'team-vilnius-wolves'})
            MATCH (away:Team {id: 'team-kaunas-green'})
            MERGE (m:Match {id: 'match-wolves-green'})
              ON CREATE SET m.sport = 'Basketball',
                            m.startTime = datetime(),
                            m.status = 'SCHEDULED'
            MERGE (m)-[:HOME_TEAM]->(home)
            MERGE (m)-[:AWAY_TEAM]->(away)
            """
        )

        # ----- Bets -----
        session.run(
            """
            MATCH (u1:User {id: 'user-arina'})
            MATCH (u2:User {id: 'user-edvinas'})
            MATCH (m:Match {id: 'match-wolves-green'})

            MERGE (b1:Bet {id: 'bet-1'})
              ON CREATE SET b1.stake = 10.0,
                            b1.odds = 2.5,
                            b1.potentialReturn = 25.0,
                            b1.status = 'OPEN',
                            b1.placedAt = datetime()

            MERGE (b2:Bet {id: 'bet-2'})
              ON CREATE SET b2.stake = 20.0,
                            b2.odds = 1.8,
                            b2.potentialReturn = 36.0,
                            b2.status = 'WON',
                            b2.placedAt = datetime()

            MERGE (u1)-[:PLACED]->(b1)
            MERGE (u2)-[:PLACED]->(b2)
            MERGE (b1)-[:ON_MATCH]->(m)
            MERGE (b2)-[:ON_MATCH]->(m)
            """
        )

        print("Seeded fixed example graph.")

def wipe_database():
    """Delete all nodes and relationships."""
    with driver.session(database="neo4j") as session:
        session.run("MATCH (n) DETACH DELETE n")
        print("All nodes and relationships deleted.")


# ---------- Flask app & endpoints ----------

app = Flask(__name__)


@app.route("/neo4j/health", methods=["GET"])
def neo4j_health():
    """Simple HTTP endpoint to verify Neo4j integration."""
    try:
        with driver.session(database="neo4j") as session:
            result = session.run("RETURN 'ok' AS status")
            record = result.single()
            status = record["status"] if record else None

        return jsonify({
            "neo4j_status": "up" if status == "ok" else "unknown",
            "query_result": status,
        }), 200
    except Exception as e:
        return jsonify({
            "neo4j_status": "down",
            "error": str(e),
        }), 500


@app.route("/neo4j/seed", methods=["POST", "GET"])
def neo4j_seed():
    """HTTP endpoint to (re)seed the fixed example graph."""
    try:
        seed_graph()
        return jsonify({"status": "ok", "message": "Graph seeded"}), 200
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route("/neo4j/delete-all", methods=["POST"])
def neo4j_delete_all():
    """
    Delete all nodes and relationships from Neo4j.
    WARNING: this wipes the whole graph.
    """
    try:
        wipe_database()
        return jsonify({"status": "ok", "message": "All data deleted"}), 200
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

if __name__ == "__main__":
    # test_connection()  # optional
    # seed_graph()       # optional direct seeding

    app.run(host="0.0.0.0", port=8000, debug=True)
