from pymongo import MongoClient
import certifi
from neo4j_connect import driver as neo4j_driver

MONGO_URI = 'mongodb+srv://arinatichonovskaja_db_user:Komanda@sportbet.wafmb2f.mongodb.net/?retryWrites=true&w=majority&appName=SportBet'
DB_NAME = "SportBET"

client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client[DB_NAME]

TEAMS = db.Team
MATCHES = db.Matches
BETS = db.Bets

def sync_team(team_doc):
    name = team_doc.get("teamName")
    sport = team_doc.get("sport")
    if not name:
        return
    with neo4j_driver.session(database="neo4j") as session:
        session.run("""
            MERGE (t:Team {name: $name})
            SET t.sport = $sport
        """, {"name": name, "sport": sport})

def sync_match(match_doc):
    match_id = str(match_doc["_id"])
    sport = match_doc.get("sport")
    date = match_doc.get("date")
    team1 = (match_doc.get("team1") or {}).get("name")
    team2 = (match_doc.get("team2") or {}).get("name")
    if not team1 or not team2:
        return

    with neo4j_driver.session(database="neo4j") as session:
        # 1) создаём/обновляем узел матча
        session.run("""
            MERGE (m:Match {id: $id})
            SET m.sport = $sport,
                m.startTime = $date,
                m.status = COALESCE(m.status, 'SCHEDULED')
        """, {"id": match_id, "sport": sport, "date": date})

        # 2) команды и связи
        session.run("""
            MERGE (t1:Team {name: $team1})
            MERGE (t2:Team {name: $team2})
            WITH t1, t2, $id AS id
            MATCH (m:Match {id: id})
            MERGE (m)-[:HOME_TEAM]->(t1)
            MERGE (m)-[:AWAY_TEAM]->(t2)
        """, {
            "id": match_id,
            "team1": team1,
            "team2": team2,
        })

def sync_bet(bet_doc):
    bet_id = str(bet_doc["_id"])
    user_email = bet_doc.get("userEmail")

    event = bet_doc.get("event") or {}
    team1 = event.get("team_1")
    team2 = event.get("team_2")
    match_type = event.get("type")
    match_date = event.get("date")

    # ключ матча в Neo4j — тот же, который вы использовали ранее
    match_key = f"{team1}|{team2}|{match_type}|{match_date}"

    with neo4j_driver.session(database="neo4j") as session:
        # --- User & Bet ---
        session.run("""
            MERGE (u:User {id: $email})
            ON CREATE SET u.createdAt = datetime()

            MERGE (b:Bet {id: $bet_id})

            MERGE (u)-[:PLACED]->(b)
        """, {
            "email": user_email,
            "bet_id": bet_id
        })

        # --- Match (узел) ---
        session.run("""
            MERGE (m:Match {id: $match_key})
            ON CREATE SET
                m.sport      = $sport,
                m.matchType  = $match_type,
                m.startTime  = $start_time,
                m.status     = COALESCE(m.status, 'SCHEDULED')
        """, {
            "match_key": match_key,
            "sport": event.get("sport"),         # если есть
            "match_type": match_type,
            "start_time": match_date
        })

        # --- Teams + связи ---
        if team1 and team2:
            session.run("""
                MERGE (t1:Team {name: $team1})
                MERGE (t2:Team {name: $team2})

                WITH t1, t2, $match_key AS match_key, $bet_id AS bet_id

                MATCH (m:Match {id: match_key})
                MATCH (b:Bet {id: bet_id})

                MERGE (m)-[:HOME_TEAM]->(t1)
                MERGE (m)-[:AWAY_TEAM]->(t2)

                MERGE (b)-[:ON_MATCH]->(m)
                MERGE (b)-[:ON_TEAM]->(t1)
                MERGE (b)-[:ON_TEAM]->(t2)
            """, {
                "team1": team1,
                "team2": team2,
                "match_key": match_key,
                "bet_id": bet_id
            })

def main():
    print("Sync TEAMS...")
    for t in TEAMS.find({}):
        sync_team(t)
    print("Teams done.")

    print("Sync MATCHES...")
    for m in MATCHES.find({}):
        sync_match(m)
    print("Matches done.")

    print("Sync BETS...")
    for b in BETS.find({}):
        sync_bet(b)
    print("Bets done.")

if __name__ == "__main__":
    main()