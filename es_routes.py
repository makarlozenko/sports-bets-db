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
            "bet_id":      {"type": "keyword"},
            "user":        {"type": "keyword"},
            "team":        {"type": "keyword"},
            "match_id":    {"type": "keyword"},
            "status":      {"type": "keyword"},
            "isWin":       {"type": "boolean"},

            "stake":       {"type": "float"},
            "odds":        {"type": "float"},
            "payout":      {"type": "float"},
            "companyOwed": {"type": "float"},

            "sport":       {"type": "keyword"},

            # matchDate kaip date su formatu yyyy-MM-dd
            "matchDate":   {"type": "date", "format": "yyyy-MM-dd"},
            "createdAt":   {"type": "date"},

            # optional, bet naudinga "per match" vaizdui
            "team1":       {"type": "keyword"},
            "team2":       {"type": "keyword"},
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
            if isinstance(r, Decimal128):
                r = r.to_decimal()
            if isinstance(r, Decimal):
                return float(r)
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



COMMISSION = 0.8

def build_es_bet_doc(bet_doc, matches_collection):
    from bson.decimal128 import Decimal128
    from datetime import datetime

    def to_float(val):
        if isinstance(val, Decimal128):
            return float(val.to_decimal())
        try:
            return float(val)
        except Exception:
            return None

    def to_iso(dt):
        return dt.isoformat() if isinstance(dt, datetime) else None

    def to_match_date(val):
        if isinstance(val, datetime):
            return val.strftime("%Y-%m-%d")
        if isinstance(val, str):
            return val.split("T")[0]
        return None

    #pagrindiniai betu laukai
    bet_id = str(bet_doc["_id"])
    status = bet_doc.get("status")
    event = bet_doc.get("event") or {}
    bet_block = bet_doc.get("bet") or {}

    stake = to_float(bet_block.get("stake")) or 0.0
    team1 = event.get("team_1")
    team2 = event.get("team_2")
    event_match_date = to_match_date(event.get("date"))

    #randame match kolekcijoje, atsizvelgiame kad teams gali buti sukeistos vietomis
    match_doc = matches_collection.find_one({
        "$or": [
            {"team1.name": team1, "team2.name": team2, "date": event_match_date},
            {"team1.name": team2, "team2.name": team1, "date": event_match_date},
        ]
    })

    match_id = str(match_doc["_id"]) if match_doc else None
    sport = match_doc.get("sport") if match_doc else None
    odds = to_float(match_doc.get("odds")) if match_doc else None
    match_date = match_doc.get("date") if match_doc else event_match_date

    #skaiciuojame laimejima ir payout, tik jei laimetas
    is_win = (status == "won")
    payout = (stake * odds) if (is_win and odds is not None) else 0.0
    company_owed = (payout * COMMISSION) if is_win else 0.0

    created_at = bet_doc.get("createdAt") or bet_block.get("createdAt")
    created_iso = to_iso(created_at)

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
        "companyOwed": company_owed,
        "sport": sport,
        "matchDate": match_date,
        "createdAt": created_iso,
        "team1": (match_doc.get("team1") or {}).get("name") if match_doc else team1,
        "team2": (match_doc.get("team2") or {}).get("name") if match_doc else team2,
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
#istrina visus indeksus ir grazina naujus, inicializuoja
def reset_indexes():

    for idx in [MATCHES_INDEX, BETS_INDEX]:
        if es.indices.exists(index=idx):
            es.indices.delete(index=idx)

    return initialize_indexes()

# ------------------------------------------
# Register routes for Flask
# ------------------------------------------

def register_es_routes(app):
    #perindeksavimas
    @app.post("/admin/reindex/matches")
    def admin_reindex_matches():
        MATCHES = app.db.Matches
        TEAMS = app.db.Team

        # 1) Pasalinam match indeksus
        if es.indices.exists(index=MATCHES_INDEX):
            es.indices.delete(index=MATCHES_INDEX)

        # 2) Sukuriam iš naujo su mapping
        es.indices.create(index=MATCHES_INDEX, body=MATCHES_MAPPING)

        # 3) Uzpildom matches is mongo
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

        # 1) Pasalinam bets_analytics indeksus
        if es.indices.exists(index=BETS_INDEX):
            es.indices.delete(index=BETS_INDEX)

        # 2) Sukuriam iš naujo su mapping
        es.indices.create(index=BETS_INDEX, body=BETS_MAPPING)

        # 3) Užpildom bets is mongo
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
    #autocomplete
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
        #kad nesikartotu
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
    #patikrina ar egzistuoja matches_search ir bets_analytics,
    #jei kažkurio nėra sukuria su atitinkamu mapping.
    def es_init():
        result = initialize_indexes()
        return jsonify({"status": "ok", "indexes": result}), 200

    @app.post("/es/reset")
    #jei indeksai egzistuoja ištrina juos,
    #tada kviečia initialize_indexes() ir sukuria iš naujo su mapping.
    def es_reset():
        result = reset_indexes()
        return jsonify({"status": "reset_ok", "indexes": result}), 200

    @app.post("/es/sync/matches")
    #užpildo / atnaujina matches_search indeksą
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

    COMMISSION = 0.8

    @app.post("/es/sync/bets")
    def sync_all_bets():
        BETS = app.db.Bets
        MATCHES = app.db.Matches

        cursor = BETS.find({})
        count = 0

        from bson.decimal128 import Decimal128
        from datetime import datetime

        def to_float(val):
            if isinstance(val, Decimal128):
                return float(val.to_decimal())
            try:
                return float(val)
            except Exception:
                return None

        def to_iso(dt):
            return dt.isoformat() if isinstance(dt, datetime) else None

        def to_match_date(val):
            # YYYY-MM-DD string
            if isinstance(val, datetime):
                return val.strftime("%Y-%m-%d")
            if isinstance(val, str):
                return val.split("T")[0]
            return None

        for doc in cursor:
            bet_id = str(doc["_id"])
            user = doc.get("userEmail")
            status = doc.get("status")

            # stake
            stake = to_float((doc.get("bet") or {}).get("stake")) or 0.0

            # event info
            event = doc.get("event") or {}
            team1 = event.get("team_1")
            team2 = event.get("team_2")

            # match date iš bet.event.date (datetime) -> YYYY-MM-DD
            event_match_date = to_match_date(event.get("date"))

            # randam match doc
            match_doc = MATCHES.find_one({
                "$or": [
                    {"team1.name": team1, "team2.name": team2, "date": event_match_date},
                    {"team1.name": team2, "team2.name": team1, "date": event_match_date},
                ]
            })

            match_id = str(match_doc["_id"]) if match_doc else None
            sport = match_doc.get("sport") if match_doc else None

            # odds iš match
            odds = to_float(match_doc.get("odds")) if match_doc else None

            # matchDate
            match_date = match_doc.get("date") if match_doc else event_match_date  # fallback jei match nerastas

            # company owed
            is_win = (status == "won")
            payout = (stake * odds) if (is_win and odds is not None) else 0.0
            company_owed = (payout * COMMISSION) if is_win else 0.0

            # createdAt – normalizuojam
            created_at = doc.get("createdAt") or (doc.get("bet") or {}).get("createdAt")
            created_at_iso = to_iso(created_at)

            body = {
                "bet_id": bet_id,
                "user": user,
                "match_id": match_id,
                "status": status,
                "isWin": is_win,
                "stake": stake,
                "odds": odds,
                "payout": payout,
                "companyOwed": company_owed,
                "sport": sport,
                "matchDate": match_date,  #  daily revenue
                "createdAt": created_at_iso,
                # optional: kad gražiai rodyt per match
                "team1": match_doc.get("team1", {}).get("name") if match_doc else team1,
                "team2": match_doc.get("team2", {}).get("name") if match_doc else team2,
            }

            es.index(index="bets_analytics", id=bet_id, document=body)
            count += 1

        return jsonify({"status": "ok", "indexed": count}), 200

    @app.get("/reports/daily-revenue")
    def daily_revenue():
        date_from = request.args.get("from")
        date_to = request.args.get("to")

        #tikrina siuos laukus, matchDate (kad galėtų dėti į dienas), match_id (kad galėtų grupuoti pagal match ir atmesti “nesusietus” betus)
        filt = [{"exists": {"field": "matchDate"}}, {"exists": {"field": "match_id"}}]

        if date_from or date_to:
            range_q = {}
            if date_from: range_q["gte"] = date_from
            if date_to:   range_q["lte"] = date_to
            filt.append({"range": {"matchDate": range_q}})

        query = {"bool": {"filter": filt}}

        aggs = {
            #grupuoja pagal dieną
            "per_day": {
                #grupuoja dokumentus pagal datą
                "date_histogram": {
                    "field": "matchDate",
                    "calendar_interval": "day",
                    "format": "yyyy-MM-dd",
                    "min_doc_count": 1 #bent vienas dokumentas tai dienai
                },
                #kiekvienoje dienoje paskaičiuoja
                "aggs": {
                    "total_stake": {"sum": {"field": "stake"}},
                    "total_owed": {"sum": {"field": "companyOwed"}},
                    "bet_count": {"value_count": {"field": "bet_id"}},
                    #dienos viduje grupuoja pagal matchą
                    "by_match": {
                        "terms": {"field": "match_id", "size": 1000},
                        "aggs": {
                            "stake": {"sum": {"field": "stake"}},
                            "owed": {"sum": {"field": "companyOwed"}},
                            "bet_count": {"value_count": {"field": "bet_id"}},
                            #duomeu paeimimas
                            "sample": {"top_hits": {"size": 1, "_source": ["team1", "team2", "sport", "matchDate"]}}
                        }
                    }
                }
            }
        }

        res = es.search(index=BETS_INDEX, query=query, aggs=aggs, size=0) #size=0 reiškia: negrąžink dokumentų

        items = []
        for day in res["aggregations"]["per_day"]["buckets"]:
            day_stake = day["total_stake"]["value"] or 0.0
            day_owed = day["total_owed"]["value"] or 0.0

            matches = []
            for m in day["by_match"]["buckets"]:
                m_stake = m["stake"]["value"] or 0.0
                m_owed = m["owed"]["value"] or 0.0
                src = (m["sample"]["hits"]["hits"][0]["_source"] if m["sample"]["hits"]["hits"] else {})

                matches.append({
                    "match_id": m["key"],
                    "team1": src.get("team1"),
                    "team2": src.get("team2"),
                    "sport": src.get("sport"),
                    "total_stake": m_stake,
                    "total_owed": m_owed,
                    "revenue": m_stake - m_owed,
                    "bet_count": m["bet_count"]["value"],
                })

            items.append({
                "date": day["key_as_string"],
                "total_stake": day_stake,
                "total_owed": day_owed,
                "revenue": day_stake - day_owed,
                "bet_count": day["bet_count"]["value"],
                "matches": matches
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
                range_q["gte"] = f"{date_from}T00:00:00"
            if date_to:
                range_q["lte"] = f"{date_to}T23:59:59"
            base_filter.append({"range": {"createdAt": range_q}})

        if base_filter:
            query = {"bool": {"filter": base_filter}}
        else:
            query = {"match_all": {}}

        aggs = {
            "by_sport": {
                "terms": {
                    "field": "sport",
                    "size": 20,
                    "order": {"bet_count": "desc"}  # Rūšiavimas pagal statymų kiekį
                },
                "aggs": {
                    "total_stake": {"sum": {"field": "stake"}},
                    "total_owed": {"sum": {"field": "companyOwed"}},  # Naudojame companyOwed
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

        # Surenkame rezultatus
        buckets = res["aggregations"]["by_sport"]["buckets"]
        items = []
        for b in buckets:
            stake = b["total_stake"]["value"] or 0.0
            owed = b["total_owed"]["value"] or 0.0
            items.append({
                "sport": b["key"],
                "bet_count": b["bet_count"]["value"],
                "total_stake": stake,
                "total_owed": owed,
                "revenue": stake - owed  # Apskaičiuojame revenue
            })

        return jsonify(items), 200
