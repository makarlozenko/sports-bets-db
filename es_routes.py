from flask import Blueprint, jsonify, request
from elasticsearch_client import es
from decimal import Decimal
es_bp = Blueprint("es_indexes", __name__)

MATCHES_INDEX = "matches_search"
BETS_INDEX = "bets_analytics"

MATCHES_MAPPING = {
    "mappings": {
        "properties": {
            "match_id":     {"type": "keyword"},
            "sport":        {"type": "keyword"}, #filtrai
            "teams":        {"type": "text"},     # "Vilnius FC vs Kaunas United"
            "team1_name":   {"type": "keyword"}, #tiksliems filtrams
            "team2_name":   {"type": "keyword"},
            "team1_rating": {"type": "float"},
            "team2_rating": {"type": "float"},
            "date":         {"type": "date"}, #filtravimui pagal datą,
            "matchType":    {"type": "keyword"}, #filtrai
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
    """Surenkamas Elasticsearch dokumentas su komandų reitingais."""

    match_id = str(doc["_id"])
    sport = doc.get("sport")
    date = doc.get("date")
    match_type = doc.get("matchType")

    team1_name = (doc.get("team1") or {}).get("name", "").strip()
    team2_name = (doc.get("team2") or {}).get("name", "").strip()

    # --- Taisymas: ieškome komandų saugiai (regex, case-insensitive)
    t1 = teams_collection.find_one({
        "teamName": {"$regex": f"^{team1_name}$", "$options": "i"},
        "sport": sport
    }) or {}

    t2 = teams_collection.find_one({
        "teamName": {"$regex": f"^{team2_name}$", "$options": "i"},
        "sport": sport
    }) or {}

    def rating_or_none(team_doc):
        r = team_doc.get("rating")
        if r is None:
            return None

        try:
            # Если Decimal128 – сначала to_decimal()
            if isinstance(r, Decimal128):
                r = r.to_decimal()
            # Если Decimal – тоже нормально
            if isinstance(r, Decimal):
                return float(r)
            # Если уже float/int/строка – float сам разберётся
            return float(r)
        except Exception:
            return None

    return {
        "match_id": match_id,
        "sport": sport,
        "teams": f"{team1_name} vs {team2_name}",
        "team1_name": team1_name,
        "team2_name": team2_name,
        "team1_rating": rating_or_none(t1),
        "team2_rating": rating_or_none(t2),
        "date": date,
        "matchType": match_type,
        "odds": to_float_odds(doc.get("odds")),
    }



def build_es_bet_doc(bet_doc, matches_collection):
    """
    Konstruojam analitinį bet dokumentą `bets_analytics` indeksui.
    Pasiimam sport ir odds iš Matches, payout suskaičiuojam čia.
    """
    from bson.decimal128 import Decimal128
    from decimal import Decimal

    def to_float(val):
        if isinstance(val, Decimal128):
            return float(val.to_decimal())
        if isinstance(val, Decimal):
            return float(val)
        try:
            return float(val)
        except Exception:
            return None

    bet_id = str(bet_doc["_id"])
    status = bet_doc.get("status")
    bet_block = bet_doc.get("bet", {}) or {}
    event = bet_doc.get("event", {}) or {}

    stake = to_float(bet_block.get("stake"))
    created_at = bet_doc.get("createdAt") or bet_block.get("createdAt")

    team1 = event.get("team_1")
    team2 = event.get("team_2")
    raw_date = event.get("date")

    # normalizuojam datą į YYYY-MM-DD
    if isinstance(raw_date, str):
        if "T" in raw_date:
            normalized_date = raw_date.split("T")[0]
        else:
            normalized_date = raw_date
    else:
        try:
            normalized_date = raw_date.strftime("%Y-%m-%d")
        except Exception:
            normalized_date = None

    # randam match Mongoje
    match_doc = matches_collection.find_one({
        "$or": [
            {"team1.name": team1, "team2.name": team2, "date": normalized_date},
            {"team1.name": team2, "team2.name": team1, "date": normalized_date},
        ]
    })

    match_id = str(match_doc["_id"]) if match_doc else None
    sport = match_doc.get("sport") if match_doc else None
    odds = to_float(match_doc.get("odds")) if match_doc else None

    is_win = (status == "won")
    payout = (stake or 0.0) * odds if (is_win and odds is not None) else 0.0

    from datetime import datetime
    if isinstance(created_at, datetime):
        created_iso = created_at.isoformat()
    else:
        created_iso = str(created_at) if created_at else None

    return {
        "bet_id": bet_id,
        "user": bet_doc.get("userEmail"),
        "team": bet_block.get("team") if bet_block.get("choice") == "winner" else None,
        "match_id": match_id,
        "status": status,
        "isWin": is_win,
        "stake": stake,
        "odds": odds,
        "payout": payout,
        "sport": sport,
        "createdAt": created_iso,
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
        TEAMS = app.db.Team

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

    @app.post("/admin/reindex/bets")
    def admin_reindex_bets():
        BETS = app.db.Bets
        MATCHES = app.db.Matches

        # 1) Dropinam bets_analytics indeksą
        if es.indices.exists(index=BETS_INDEX):
            es.indices.delete(index=BETS_INDEX)

        # 2) Sukuriam iš naujo su mapping
        es.indices.create(index=BETS_INDEX, body=BETS_MAPPING)

        # 3) Užpildom iš Mongo.Bets
        count = 0
        for bet_doc in BETS.find({}):
            body = build_es_bet_doc(bet_doc, MATCHES)
            es.index(index=BETS_INDEX, id=str(bet_doc["_id"]), document=body)
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
        TEAMS = app.db.Team
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

    @app.get("/reports/daily-revenue")
    def daily_revenue():
        """
        Finansinė analitika: pajamos per dieną.
        Gražina masyvą, kur kiekvienai dienai:
        - date
        - total_stake
        - total_payout
        - bet_count
        """
        date_from = request.args.get("from")  # YYYY-MM-DD
        date_to = request.args.get("to")  # YYYY-MM-DD

        # Range ant createdAt
        if date_from or date_to:
            range_q = {}
            if date_from:
                range_q["gte"] = f"{date_from}T00:00:00Z"
            if date_to:
                range_q["lte"] = f"{date_to}T23:59:59Z"
            query = {"range": {"createdAt": range_q}}
        else:
            query = {"match_all": {}}

        aggs = {
            "per_day": {
                "date_histogram": {
                    "field": "createdAt",
                    "calendar_interval": "day",
                    "format": "yyyy-MM-dd",
                    "min_doc_count": 0
                },
                "aggs": {
                    "total_stake": {"sum": {"field": "stake"}},
                    "total_payout": {"sum": {"field": "payout"}},
                    "bet_count": {"value_count": {"field": "bet_id"}}
                }
            }
        }

        res = es.search(
            index=BETS_INDEX,
            query=query,
            aggs=aggs,
            size=0
        )

        buckets = res["aggregations"]["per_day"]["buckets"]
        items = []
        for b in buckets:
            items.append({
                "date": b["key_as_string"],
                "total_stake": b["total_stake"]["value"],
                "total_payout": b["total_payout"]["value"],
                "bet_count": b["bet_count"]["value"],
            })

        return jsonify(items), 200

    @app.get("/reports/sport-popularity")
    def sport_popularity():
        """
        Statistika pagal sporto šakas:
        - kiek statymų
        - kokia bendra statymų suma
        - kiek laimėta (payout)
        """
        date_from = request.args.get("from")
        date_to = request.args.get("to")

        base_filter = []

        if date_from or date_to:
            range_q = {}
            if date_from:
                range_q["gte"] = f"{date_from}T00:00:00Z"
            if date_to:
                range_q["lte"] = f"{date_to}T23:59:59Z"
            base_filter.append({"range": {"createdAt": range_q}})

        if base_filter:
            query = {"bool": {"filter": base_filter}}
        else:
            query = {"match_all": {}}

        aggs = {
            "by_sport": {
                "terms": {
                    "field": "sport",
                    "size": 20
                },
                "aggs": {
                    "total_stake": {"sum": {"field": "stake"}},
                    "total_payout": {"sum": {"field": "payout"}},
                    "bet_count": {"value_count": {"field": "bet_id"}}
                }
            }
        }

        res = es.search(
            index=BETS_INDEX,
            query=query,
            aggs=aggs,
            size=0
        )

        buckets = res["aggregations"]["by_sport"]["buckets"]
        items = []
        for b in buckets:
            items.append({
                "sport": b["key"],
                "bet_count": b["bet_count"]["value"],
                "total_stake": b["total_stake"]["value"],
                "total_payout": b["total_payout"]["value"],
            })

        return jsonify(items), 200

