from flask import Blueprint, jsonify, request
from elasticsearch_client import es

es_bp = Blueprint("es_indexes", __name__)

MATCHES_INDEX = "matches_search"
BETS_INDEX = "bets_analytics"

MATCHES_MAPPING = {
    "mappings": {
        "properties": {
            "match_id":     {"type": "keyword"},
            "sport":        {"type": "keyword"},
            "teams":        {"type": "text"},     # "Vilnius FC vs Kaunas United"
            "team1_name":   {"type": "keyword"},
            "team2_name":   {"type": "keyword"},
            "team1_rating": {"type": "float"},
            "team2_rating": {"type": "float"},
            "date":         {"type": "date"},
            "matchType":    {"type": "keyword"},
            "odds":         {"type": "float"},
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

def build_es_match_doc(doc, teams_collection):
    """Собрать документ матча для Elasticsearch с именами и рейтингами команд."""
    match_id = str(doc["_id"])
    sport = doc.get("sport")
    date = doc.get("date")
    match_type = doc.get("matchType")

    team1_name = (doc.get("team1") or {}).get("name")
    team2_name = (doc.get("team2") or {}).get("name")

    # тянем рейтинг из Mongo.Teams
    t1 = teams_collection.find_one({"name": team1_name}) or {}
    t2 = teams_collection.find_one({"name": team2_name}) or {}

    def rating_or_none(team_doc):
        r = team_doc.get("rating")
        return float(r) if r is not None else None

    return {
        "match_id":     match_id,
        "sport":        sport,
        "teams":        f"{team1_name} vs {team2_name}",
        "team1_name":   team1_name,
        "team2_name":   team2_name,
        "team1_rating": rating_or_none(t1),
        "team2_rating": rating_or_none(t2),
        "date":         date,
        "matchType":    match_type,
        "odds":         to_float_odds(doc.get("odds")),
    }


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
    @app.post("/admin/reindex/matches")
    def admin_reindex_matches():
        MATCHES = app.db.Matches
        TEAMS = app.db.Teams

        # 1) дропаем только индекс матчей
        if es.indices.exists(index=MATCHES_INDEX):
            es.indices.delete(index=MATCHES_INDEX)

        # 2) создаём заново с mapping
        es.indices.create(index=MATCHES_INDEX, body=MATCHES_MAPPING)

        # 3) заливаем все матчи
        count = 0
        for doc in MATCHES.find({}):
            body = build_es_match_doc(doc, TEAMS)
            es.index(index=MATCHES_INDEX, id=str(doc["_id"]), document=body)
            count += 1

        return jsonify({
            "status": "ok",
            "reindexed": count
        }), 200

    @app.get("/search/matches")
    def search_matches():
        team = request.args.get("team", "").strip()
        sport = request.args.get("sport", "").strip()
        date_from = request.args.get("from")
        date_to = request.args.get("to")

        must = []
        filt = []

        if team:
            must.append({
                "multi_match": {
                    "query": team,
                    "fields": ["teams^2", "team1_name", "team2_name"]
                }
            })

        if sport:
            filt.append({"term": {"sport": sport}})

        if date_from or date_to:
            range_q = {}
            if date_from:
                range_q["gte"] = date_from
            if date_to:
                range_q["lte"] = date_to
            filt.append({"range": {"date": range_q}})

        if not must and not filt:
            # ничего не задано – вернём пустой ответ
            return jsonify({"total": 0, "items": []}), 200

        query = {"bool": {}}
        if must:
            query["bool"]["must"] = must
        if filt:
            query["bool"]["filter"] = filt

        res = es.search(
            index=MATCHES_INDEX,
            query=query,
            size=50
        )

        hits = res["hits"]["hits"]
        items = [
            {
                "match_id": h["_source"]["match_id"],
                "sport": h["_source"].get("sport"),
                "teams": h["_source"].get("teams"),
                "team1_rating": h["_source"].get("team1_rating"),
                "team2_rating": h["_source"].get("team2_rating"),
                "date": h["_source"].get("date"),
                "matchType": h["_source"].get("matchType"),
                "score": h["_score"],
            }
            for h in hits
        ]

        return jsonify({
            "total": res["hits"]["total"]["value"],
            "items": items
        }), 200

    @app.get("/search/teams")
    def search_teams():
        q = request.args.get("q", "").strip()
        if not q:
            return jsonify({"teams": []}), 200

        res = es.search(
            index=MATCHES_INDEX,
            query={
                "match_phrase_prefix": {
                    "teams": {
                        "query": q
                    }
                }
            },
            size=50
        )

        q_lower = q.lower()
        suggestions = set()

        for hit in res["hits"]["hits"]:
            teams_text = hit["_source"].get("teams") or ""
            for name in teams_text.split(" vs "):
                name_clean = name.strip()
                if name_clean.lower().startswith(q_lower):
                    suggestions.add(name_clean)

        return jsonify({
            "query": q,
            "teams": sorted(suggestions)
        }), 200

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
        TEAMS = app.db.Teams
        cursor = MATCHES.find({})
        count = 0

        for doc in cursor:
            match_id = str(doc["_id"])
            body = build_es_match_doc(doc, TEAMS)
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


