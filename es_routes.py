from flask import Blueprint, jsonify
from elasticsearch_client import es

es_bp = Blueprint("es_indexes", __name__)

MATCHES_INDEX = "matches_search"
BETS_INDEX = "bets_analytics"

MATCHES_MAPPING = {
    "mappings": {
        "properties": {
            "match_id": {"type": "keyword"},
            "sport": {"type": "keyword"},
            "teams": {"type": "text"},
            "date": {"type": "date"},
            "matchType": {"type": "keyword"},
            "odds": {"type": "float"}
        }
    }
}

BETS_MAPPING = {
    "mappings": {
        "properties": {
            "bet_id": {"type": "keyword"},
            "user": {"type": "keyword"},
            "team": {"type": "keyword"},
            "match_id": {"type": "keyword"},
            "status": {"type": "keyword"},
            "stake": {"type": "float"},
            "odds": {"type": "float"},
            "sport": {"type": "keyword"},
            "createdAt": {"type": "date"}
        }
    }
}
from bson.decimal128 import Decimal128

def to_float_odds(value):
    if isinstance(value, Decimal128):
        return float(value.to_decimal())
    try:
        return float(value)
    except:
        return 0.0


# ------------------------------------------
# Create indexes
# ------------------------------------------

def initialize_indexes():

    if not es.indices.exists(index=MATCHES_INDEX):
        es.indices.create(index=MATCHES_INDEX, body=MATCHES_MAPPING)

    if not es.indices.exists(index=BETS_INDEX):
        es.indices.create(index=BETS_INDEX, body=BETS_MAPPING)

    return {
        "matches_search": "ready",
        "bets_analytics": "ready"
    }

# ------------------------------------------
# Reset indexes
# ------------------------------------------

def reset_indexes():

    for idx in [MATCHES_INDEX, BETS_INDEX]:
        if es.indices.exists(index=idx):
            es.indices.delete(index=idx)

    return initialize_indexes()

# ------------------------------------------
# Register routes for Flask
# ------------------------------------------

def register_es_routes(app):

    @app.post("/es/init")
    def es_init():
        result = initialize_indexes()
        return jsonify({"status": "ok", "indexes": result}), 200

    @app.post("/es/reset")
    def es_reset():
        result = reset_indexes()
        return jsonify({"status": "reset_ok", "indexes": result}), 200

    @app.post("/es/sync/matches")
    def sync_all_matches():
        MATCHES = app.db.Matches
        cursor = MATCHES.find({})
        count = 0

        for doc in cursor:
            match_id = str(doc["_id"])
            body = {
                "match_id": match_id,
                "sport": doc.get("sport"),
                "teams": f"{doc['team1']['name']} vs {doc['team2']['name']}",
                "date": doc.get("date"),
                "matchType": doc.get("matchType"),
                "odds": to_float_odds(doc.get("odds")),
            }
            es.index(index=MATCHES_INDEX, id=match_id, document=body)
            count += 1

        return jsonify({"status": "ok", "indexed": count}), 200

    @app.post("/es/sync/bets")
    def sync_all_bets():
        BETS = app.db.Bets
        MATCHES = app.db.Matches

        cursor = BETS.find({})
        count = 0

        from bson.decimal128 import Decimal128

        def to_float(val):
            if isinstance(val, Decimal128):
                return float(val.to_decimal())
            if isinstance(val, dict):
                return None
            try:
                return float(val)
            except:
                return None

        for doc in cursor:
            bet_id = str(doc["_id"])
            user = doc.get("userEmail")
            status = doc.get("status")

            # createdAt (in bet or top-level)
            created_at = doc.get("createdAt") or doc.get("bet", {}).get("createdAt")

            # stake - correct Decimal128 handling
            stake = to_float(doc.get("bet", {}).get("stake"))

            # team - only for winner
            choice = doc.get("bet", {}).get("choice")
            team = doc.get("bet", {}).get("team") if choice == "winner" else None

            # event info
            event = doc.get("event", {})
            team1 = event.get("team_1")
            team2 = event.get("team_2")

            # ---- FIX DATE MATCH ----
            raw_date = event.get("date")

            # if ISO -> convert to YYYY-MM-DD
            if isinstance(raw_date, str):
                if "T" in raw_date:
                    normalized_date = raw_date.split("T")[0]
                else:
                    normalized_date = raw_date
            else:
                # Mongo datetime → convert to string
                try:
                    normalized_date = raw_date.strftime("%Y-%m-%d")
                except:
                    normalized_date = None

            # find match in Mongo
            match_doc = MATCHES.find_one({
                "$or": [
                    {"team1.name": team1, "team2.name": team2, "date": normalized_date},
                    {"team1.name": team2, "team2.name": team1, "date": normalized_date}
                ]
            })

            match_id = str(match_doc["_id"]) if match_doc else None
            sport = match_doc.get("sport") if match_doc else None

            # odds - from match
            odds = to_float(match_doc.get("odds")) if match_doc else None

            # final ES document
            body = {
                "bet_id": bet_id,
                "user": user,
                "team": team,
                "match_id": match_id,
                "status": status,
                "stake": stake,
                "odds": odds,
                "sport": sport,
                "createdAt": created_at
            }

            es.index(index="bets_analytics", id=bet_id, document=body)
            count += 1

        return jsonify({"status": "ok", "indexed": count}), 200


