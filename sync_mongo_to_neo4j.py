from pymongo import MongoClient
import certifi
from neo4j_connect import driver as neo4j_driver
from bson.decimal128 import Decimal128
from datetime import datetime

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
            MERGE (t:Team {name: $name, sport: $sport})
        """, {"name": name, "sport": sport})


def sync_match(match_doc):
    match_id = str(match_doc["_id"])
    sport = match_doc.get("sport")
    raw_date = match_doc.get("date")
    match_type = match_doc.get("matchType")
    team1 = (match_doc.get("team1") or {}).get("name")
    team2 = (match_doc.get("team2") or {}).get("name")
    if not team1 or not team2:
        return

    # normalizuojam datą į 'YYYY-MM-DD' string
    if isinstance(raw_date, datetime):
        date_key = raw_date.date().isoformat()
    else:
        date_key = str(raw_date)

    with neo4j_driver.session(database="neo4j") as session:
        session.run("""
            MERGE (m:Match {id: $id})
            SET m.sport     = $sport,
                m.startTime = $date_key,
                m.matchType = $match_type
        """, {
            "id": match_id,
            "sport": sport,
            "date_key": date_key,
            "match_type": match_type,
        })

        session.run("""
            MERGE (t1:Team {name: $team1, sport: $sport})
            MERGE (t2:Team {name: $team2, sport: $sport})
            WITH t1, t2, $id AS id
            MATCH (m:Match {id: id})
            MERGE (m)-[:HOME_TEAM]->(t1)
            MERGE (m)-[:AWAY_TEAM]->(t2)
        """, {
            "id": match_id,
            "team1": team1,
            "team2": team2,
            "sport": sport,
        })


def sync_bet(bet_doc):
    bet_id = str(bet_doc["_id"])
    user_email = bet_doc.get("userEmail")
    user_nickname = bet_doc.get("nickname")

    # ----- EVENT (mačo identifikacija) -----
    event = bet_doc.get("event") or {}
    team1 = event.get("team_1")
    team2 = event.get("team_2")
    match_type = event.get("type")
    raw_match_date = event.get("date")
    sport = event.get("sport") or bet_doc.get("sport")

    has_match_info = bool(team1 and team2 and match_type and raw_match_date)

    # ----- BET LAUKAI -----
    bet_info = bet_doc.get("bet") or {}

    choice = bet_info.get("choice")          # pvz. "winner" arba "score"
    bet_team = bet_info.get("team")          # komanda, ant kurios stato (winner bet)
    stake = bet_info.get("stake")
    bet_created_at = bet_info.get("createdAt")

    # STATUS – šaknyje: "won" / "lost"
    bet_status = bet_doc.get("status")

    # Decimal128 -> float
    if isinstance(stake, Decimal128):
        stake = float(stake.to_decimal())

    # ----- normalizuojam datą, kad sutaptų su Match.startTime -----
    start_time_key = None
    if raw_match_date is not None:
        if isinstance(raw_match_date, datetime):
            start_time_key = raw_match_date.date().isoformat()  # "YYYY-MM-DD"
        else:
            # jei Mongo saugo kaip string "2025-09-01" – tiesiog pavertėm į str
            start_time_key = str(raw_match_date)

    with neo4j_driver.session(database="neo4j") as session:
        # ----- User & Bet -----
        session.run("""
            MERGE (u:User {id: $email})
            ON CREATE SET 
                u.createdAt = datetime(),
                u.nickname  = $nickname
            ON MATCH SET
                u.nickname  = coalesce(u.nickname, $nickname)

            MERGE (b:Bet {id: $bet_id})
            SET b.choice    = $choice,
                b.team      = $bet_team,
                b.stake     = $stake,
                b.status    = $bet_status,
                b.createdAt = $bet_created_at

            MERGE (u)-[:PLACED]->(b)
        """, {
            "email": user_email,
            "nickname": user_nickname,
            "bet_id": bet_id,
            "choice": choice,
            "bet_team": bet_team,
            "stake": stake,
            "bet_status": bet_status,
            "bet_created_at": bet_created_at
        })

        # ----- Ryšys su MATCH (VISADA, jei turim info) -----
        if has_match_info and start_time_key:
            params = {
                "team1": team1,
                "team2": team2,
                "match_type": match_type,
                "start_time": start_time_key,
                "bet_id": bet_id,
            }

            if sport:
                params["sport"] = sport
                match_query = """
                    MATCH (t1:Team {name: $team1, sport: $sport})
                    MATCH (t2:Team {name: $team2, sport: $sport})
                    MATCH (m:Match {matchType: $match_type, startTime: $start_time, sport: $sport})
                    MATCH (m)-[:HOME_TEAM]->(t1)
                    MATCH (m)-[:AWAY_TEAM]->(t2)
                    MATCH (b:Bet {id: $bet_id})

                    MERGE (b)-[:ON_MATCH]->(m)
                """
            else:
                match_query = """
                    MATCH (t1:Team {name: $team1})
                    MATCH (t2:Team {name: $team2})
                    MATCH (m:Match {matchType: $match_type, startTime: $start_time})
                    MATCH (m)-[:HOME_TEAM]->(t1)
                    MATCH (m)-[:AWAY_TEAM]->(t2)
                    MATCH (b:Bet {id: $bet_id})

                    MERGE (b)-[:ON_MATCH]->(m)
                """

            session.run(match_query, params)

        # ----- Ryšys ON_TEAM – tik jei betas yra team-specific (winner) -----
        if choice == "winner" and bet_team:
            team_params = {"bet_id": bet_id, "bet_team": bet_team}
            if sport:
                team_params["sport"] = sport
                session.run("""
                    MATCH (b:Bet {id: $bet_id})
                    MATCH (t:Team {name: $bet_team, sport: $sport})
                    MERGE (b)-[:ON_TEAM]->(t)
                """, team_params)
            else:
                session.run("""
                    MATCH (b:Bet {id: $bet_id})
                    MATCH (t:Team {name: $bet_team})
                    MERGE (b)-[:ON_TEAM]->(t)
                """, team_params)



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