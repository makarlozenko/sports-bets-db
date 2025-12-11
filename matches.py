from flask import request, jsonify, current_app
from bson import ObjectId
from datetime import datetime
from dateutil import parser
from bson.decimal128 import Decimal128
from decimal import Decimal, ROUND_HALF_UP

from RedisApp import cache_get_json, cache_set_json, invalidate, invalidate_pattern
from neo4j_connect import driver as neo4j_driver
from elasticsearch_client import es
from es_routes import build_es_match_doc

def register_matches_routes(app, db):
    MATCHES = db.Matches   # collection
    TEAMS = db.Team

    def to_oid(s):
        try:
            return ObjectId(s)
        except Exception:
            return None

    def parse_dt(s):
        try:
            return parser.isoparse(s)
        except Exception:
            return None

    def ser(doc):
        """Serialize MongoDB ObjectId and nested structures."""
        if not doc:
            return None
        d = dict(doc)
        for k, v in d.items():
            if isinstance(v, ObjectId):
                d[k] = str(v)
            elif isinstance(v, dict):
                d[k] = ser(v)
            elif isinstance(v, list):
                d[k] = [ser(x) if isinstance(x, dict) else x for x in v]
        return d

    def ser_mongo(x):
        if isinstance(x, dict):
            return {k: ser_mongo(v) for k, v in x.items()}
        if isinstance(x, list):
            return [ser_mongo(v) for v in x]
        if isinstance(x, ObjectId):
            return str(x)
        if isinstance(x, datetime):
            return x.isoformat() + "Z"
        if isinstance(x, Decimal128):
            # kaip tekstą, kad nelaužytume tikslumo
            return str(x.to_decimal())
        if isinstance(x, Decimal):
            return str(x)
        return x

    from datetime import datetime

    def es_match_body(match_doc):
        """Paruošti match dokumentą Elasticsearch indeksui matches_search."""

        team1_name = (match_doc.get("team1") or {}).get("name")
        team2_name = (match_doc.get("team2") or {}).get("name")
        sport = match_doc.get("sport")

        # --- pasiimam reitingus iš Mongo Teams kolekcijos ---
        # Team dokumente laukai: teamName, sport, rating
        t1 = TEAMS.find_one({"teamName": team1_name, "sport": sport}) or {}
        t2 = TEAMS.find_one({"teamName": team2_name, "sport": sport}) or {}

        def rating_or_none(team_doc):
            r = team_doc.get("rating")
            try:
                return float(r) if r is not None else None
            except (TypeError, ValueError):
                return None

        return {
            # atitinka MATCHES_MAPPING: "match_id": {"type": "keyword"}
            "match_id": str(match_doc["_id"]),
            "sport": sport,
            # tekstinis laukas "Vilnius FC vs Kaunas United" paieškai/autocomplete
            "teams": f"{team1_name} vs {team2_name}",
            # keyword laukai filtrams / grupavimui
            "team1_name": team1_name,
            "team2_name": team2_name,
            # praturtinimas iš Teams kolekcijos
            "team1_rating": rating_or_none(t1),
            "team2_rating": rating_or_none(t2),
            # data – eina kaip datetime, ES pats susitvarkys kaip "date" tipą
            "date": match_doc.get("date"),
            "matchType": match_doc.get("matchType"),
            "odds": float(match_doc.get("odds")) if match_doc.get("odds") is not None else None,
        }

    def sync_match_to_neo4j(match_doc):
        match_id = str(match_doc["_id"])
        sport = match_doc.get("sport")
        raw_date = match_doc.get("date")
        match_type = match_doc.get("matchType")
        team1 = (match_doc.get("team1") or {}).get("name")
        team2 = (match_doc.get("team2") or {}).get("name")

        if not team1 or not team2:
            return

        # normalizuojam datą į 'YYYY-MM-DD' string,
        # kad sutaptų su tuo, ką naudoja Bets -> ON_MATCH
        if isinstance(raw_date, datetime):
            start_time_key = raw_date.date().isoformat()
        else:
            start_time_key = str(raw_date)

        with neo4j_driver.session(database="neo4j") as session:
            # Match
            session.run("""
                MERGE (m:Match {id: $id})
                SET m.sport     = $sport,
                    m.startTime = $start_time,
                    m.matchType = $match_type,
                    m.status    = COALESCE(m.status, 'SCHEDULED')
            """, {
                "id": match_id,
                "sport": sport,
                "start_time": start_time_key,
                "match_type": match_type,
            })

            # Teams + ryšiai
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

            # RIVAL_OF logika
            pair_filter = {
                "$or": [
                    {"team1.name": team1, "team2.name": team2},
                    {"team1.name": team2, "team2.name": team1},
                ]
            }
            games = MATCHES.count_documents(pair_filter)
            if games >= 3:
                session.run(
                    """
                    MATCH (t1:Team {name: $t1, sport: $sport}), (t2:Team {name: $t2, sport: $sport})
                    MERGE (t1)-[:RIVAL_OF]-(t2)
                    """,
                    {"t1": team1, "t2": team2, "sport": sport}
                )

    # ---------------------- CRUD ----------------------
    @app.get("/matches")
    def list_matches():
        try:
            sport = request.args.get("sport")
            date_from = parse_dt(request.args.get("from"))
            date_to = parse_dt(request.args.get("to"))

            sort_by = request.args.get("sort_by", "date")
            ascending = request.args.get("ascending", "false").lower() == "true"
            order = 1 if ascending else -1

            cache_key = f"matches:list:{sport or 'all'}:{date_from}:{date_to}:{sort_by}:{ascending}"
            cached = cache_get_json(cache_key)
            if cached:
                return jsonify(cached), 200

            query = {}
            if sport:
                query["sport"] = sport
            if date_from or date_to:
                date_query = {}
                if date_from: date_query["$gte"] = date_from
                if date_to:   date_query["$lte"] = date_to
                query["date"] = date_query

            total = MATCHES.count_documents(query)
            cur = MATCHES.find(query).sort(sort_by, order)

            # NAUJA: rekursyviai serializuojame kiekvieną dokumentą
            items = [ser_mongo(doc) for doc in cur]

            result = {"items": items, "total": total}
            cache_set_json(cache_key, result, ttl=45)
            return jsonify(result), 200
        except Exception as e:
            return jsonify({"message": "Failed to list matches.", "error": str(e)}), 400

    @app.get("/matches/<id>")
    def get_match(id):
        """Get match by ID."""
        oid = to_oid(id)
        if not oid:
            return jsonify({"error": "Invalid id"}), 400
        doc = MATCHES.find_one({"_id": oid})
        if not doc:
            return jsonify({"error": "Not found"}), 404
        return jsonify(ser(doc))

    #----------- POST ----------------
    FORM_N_GAMES = 10
    SMOOTH_ALPHA = 1.0
    DEFAULT_RATING = 1500
    LOGISTIC_SCALE = 400.0
    FORM_WEIGHT = 0.6  # kiek svarbi forma prieš rating
    MARGIN = Decimal("1.06")
    ODDS_MIN = Decimal("0.50")  #ne mažiau kaip 0.50
    ODDS_MAX = Decimal("10.00")  #ir ne daugiau kaip 10.00

    def _q2(x) -> Decimal:
        return Decimal(x).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _team_form_winrate(team_name: str) -> float:
        """
        Win-rate su Laplace švelninimu iš paskutinių N rungtynių:
        (wins + 0.5*draws + alpha) / (games + 2*alpha).
        Jei istorijos nėra — 0.5 (neutraliai).
        """
        cursor = (MATCHES.find({
            "$or": [{"team1.name": team_name}, {"team2.name": team_name}]
        }).sort("date", -1).limit(FORM_N_GAMES))

        wins = draws = games = 0
        for m in cursor:
            if m.get("team1", {}).get("name") == team_name:
                st = (m.get("team1", {}).get("result") or {}).get("status")
            else:
                st = (m.get("team2", {}).get("result") or {}).get("status")
            if not st:
                continue
            games += 1
            s = str(st).lower()
            if s == "win":
                wins += 1
            elif s == "draw":
                draws += 1

        num = wins + 0.5 * draws + SMOOTH_ALPHA
        den = games + 2 * SMOOTH_ALPHA
        return float(num / den) if den > 0 else 0.5

    def _rating_prob(team1: str, team2: str) -> float:
        """
        Tikimybė pagal rating skirtumą (Bradley–Terry / Elo logit).
        """
        # TEISINGAS MONGO LAUKAS: teamName + sport
        t1 = TEAMS.find_one({"teamName": team1, "sport": sport}) or {}
        t2 = TEAMS.find_one({"teamName": team2, "sport": sport}) or {}

        r1 = float(t1.get("rating", DEFAULT_RATING))
        r2 = float(t2.get("rating", DEFAULT_RATING))

        diff = r1 - r2
        return 1.0 / (1.0 + 10.0 ** (-diff / LOGISTIC_SCALE))

    def _compute_probs(team1: str, team2: str, sport: str) -> tuple[float, float]:
        f1 = _team_form_winrate(team1)
        f2 = _team_form_winrate(team2)

        if f1 + f2 > 0:
            s = f1 + f2
            f1, f2 = f1 / s, f2 / s
        else:
            f1 = f2 = 0.5

        pr1 = _rating_prob(team1, team2)  # NAUDOJA TEISINGĄ RATING lookup
        p1 = FORM_WEIGHT * f1 + (1.0 - FORM_WEIGHT) * pr1

        p1 = max(0.001, min(0.999, p1))
        p2 = 1.0 - p1
        return p1, p2

    def _odds_from_prob(p: float) -> Decimal:
        """odds = 1/p, + margin, ribos [0.50, 10.00], apvalinta iki 2 d.p."""
        o = Decimal(1.0 / max(1e-9, p)) * MARGIN
        o = max(ODDS_MIN, min(ODDS_MAX, o))
        return _q2(o)

    @app.post("/matches")
    def create_match():
        """Sukurti naują match (su dubliavimo patikra) ir automatiškai paskaičiuoti odds."""
        try:
            data = request.get_json(silent=True) or {}
            now = datetime.utcnow()
            data.setdefault("created_at", now)
            data.setdefault("updated_at", now)

            # --- privalomi laukai ---
            sport = data.get("sport")
            match_type = data.get("matchType")
            date = data.get("date")
            team1 = (data.get("team1") or {}).get("name")
            team2 = (data.get("team2") or {}).get("name")

            if not all([sport, match_type, date, team1, team2]):
                return jsonify({"error": "Missing required match fields"}), 400

            # --- dubliavimo patikra ---
            duplicate = MATCHES.find_one({
                "sport": sport,
                "matchType": match_type,
                "date": date,
                "team1.name": team1,
                "team2.name": team2
            })
            if duplicate:
                return jsonify({
                    "error": "Duplicate match already exists for this date and teams",
                    "existing_match": ser_mongo(duplicate)
                }), 409

            # --- auto-odds (forma + rating) ---
            p1, p2 = _compute_probs(team1, team2, sport)
            o1 = _odds_from_prob(p1)
            o2 = _odds_from_prob(p2)

            # Įrašom abi puses, o į "odds" dedam underdogo koefą (didesnį)
            data["oddsDetail"] = {"team1": Decimal128(o1), "team2": Decimal128(o2)}
            data["odds"] = Decimal128(max(o1, o2))

            # --- įrašymas ---
            res = MATCHES.insert_one(data)
            new_doc = MATCHES.find_one({"_id": res.inserted_id})

            # ---- Sync to Elasticsearch ----
            try:
                TEAMS = app.db.Team
                es.index(
                    index="matches_search",
                    id=str(res.inserted_id),
                    document=build_es_match_doc(new_doc, TEAMS)
                )

            except Exception as e:
                current_app.logger.error(f"ES sync error (create match): {e}")

            try:
                sync_match_to_neo4j(new_doc)
            except Exception as e:
                current_app.logger.exception("Failed to sync match to Neo4j: %s", e)

            invalidate_pattern("matches:list:*")
            invalidate_pattern("matches_filter:*")
            invalidate_pattern("matches_reorder:*")

            return jsonify({"message": "Match added", "match": ser_mongo(new_doc)}), 201

        except Exception as e:
            return jsonify({"error": str(e)}), 400

    @app.patch("/matches/<id>")
    def update_match(id):
        """Update existing match."""
        oid = to_oid(id)
        if not oid:
            return jsonify({"error": "Invalid id"}), 400

        data = request.get_json(silent=True) or {}
        data["updated_at"] = datetime.utcnow()
        upd = MATCHES.update_one({"_id": oid}, {"$set": data})

        if not upd.matched_count:
            return jsonify({"error": "Not found"}), 404

        invalidate_pattern("matches:list:*")
        invalidate_pattern("matches_filter:*")
        invalidate_pattern("matches_reorder:*")

        doc = MATCHES.find_one({"_id": oid})

        # Sync update to Elasticsearch
        try:
            updated = MATCHES.find_one({"_id": oid})
            es.index(
                index="matches_search",
                id=str(oid),
                document=build_es_match_doc(updated, TEAMS)
            )
        except Exception as e:
            current_app.logger.error(f"ES sync error (update match): {e}")

        return jsonify(ser(doc))

    @app.delete("/matches/<id>")
    def delete_match(id):
        """Delete match by ID (Mongo + Neo4j)."""
        oid = to_oid(id)
        if not oid:
            return jsonify({"error": "Invalid id"}), 400

        # 1)ieskom rungtyniu Mongo
        match_doc = MATCHES.find_one({"_id": oid})
        if not match_doc:
            return jsonify({"error": "Not found"}), 404

        team1 = (match_doc.get("team1") or {}).get("name")
        team2 = (match_doc.get("team2") or {}).get("name")
        match_id = str(oid)
        sport = match_doc.get("sport")


        # 2)trinam is Mongo
        res = MATCHES.delete_one({"_id": oid})
        if not res.deleted_count:
            return jsonify({"error": "Not found"}), 404

        # 3)Neo4j
        try:
            with neo4j_driver.session(database="neo4j") as session:
                # 3.1 Pirma ištrinam VISUS Bet, kurie susieti su šiuo match
                session.run("""
                    MATCH (m:Match {id: $id})<-[:ON_MATCH]-(b:Bet)
                    DETACH DELETE b
                """, {"id": match_id})

                # 3.2 Tada ištrinam patį Match (HOME_TEAM, AWAY_TEAM, ir t.t.)
                session.run("""
                    MATCH (m:Match {id: $id})
                    DETACH DELETE m
                """, {"id": match_id})

                # 3.3 RIVAL_OF – paliekam kaip buvo
                if team1 and team2:
                    pair_filter = {
                        "$or": [
                            {"team1.name": team1, "team2.name": team2},
                            {"team1.name": team2, "team2.name": team1},
                        ]
                    }
                    games = MATCHES.count_documents(pair_filter)

                    if games < 3 and sport:
                        session.run(
                            """
                            MATCH (t1:Team {name: $t1, sport: $sport})-[r:RIVAL_OF]-
                                  (t2:Team {name: $t2, sport: $sport})
                            DELETE r
                            """,
                            {"t1": team1, "t2": team2, "sport": sport}
                        )

        except Exception as e:
            current_app.logger.exception("Failed to sync match delete to Neo4j: %s", e)


        # 4)trinam cash'a
        invalidate_pattern("matches:list:*")
        invalidate_pattern("matches_filter:*")
        invalidate_pattern("matches_reorder:*")

        # Sync delete to Elasticsearch
        try:
            es.delete(index="matches_search", id=str(oid))
        except Exception as e:
            current_app.logger.error(f"ES sync error (delete match): {e}")

        return jsonify({"deleted": True, "_id": id})

    # ---------------------- FILTER ----------------------

    @app.get("/matches/filter")
    def filter_matches():
        """
        Filter matches by sport, team name, or date range.
        Example: /matches/filter?sport=football&team=Vilnius&from=2025-09-01
        """
        sport = request.args.get("sport")
        team = request.args.get("team")
        date_from = request.args.get("from")
        date_to = request.args.get("to")

        cache_key = f"matches_filter:{sport}:{team}:{date_from}:{date_to}"
        cached = cache_get_json(cache_key)
        if cached:
            return jsonify(cached), 200

        query = {}
        if sport:
            query["sport"] = sport
        if team:
            query["$or"] = [
                {"team1.name": {"$regex": team, "$options": "i"}},
                {"team2.name": {"$regex": team, "$options": "i"}}
            ]
        if date_from or date_to:
            date_query = {}
            if date_from:
                date_query["$gte"] = date_from
            if date_to:
                date_query["$lte"] = date_to
            query["date"] = date_query

        cur = MATCHES.find(query)
        items = [ser(x) for x in cur]
        result = {"items": items, "total": len(items)}

        cache_set_json(cache_key, result, ttl=45)
        return jsonify(result)

    # ---------------------- REORDER ----------------------
    @app.get("/matches/reorder")
    def reorder_matches():
        """
        Sort matches by date or sport.
        Example: /matches/reorder?sort_by=date&ascending=false
        """
        sort_by = request.args.get("sort_by", "date")
        ascending = request.args.get("ascending", "true").lower() == "true"

        cache_key = f"matches_reorder:{sort_by}:{ascending}"
        cached = cache_get_json(cache_key)
        if cached:
            return jsonify(cached), 200

        order = 1 if ascending else -1

        cur = MATCHES.find({}).sort(sort_by, order)
        items = [ser(x) for x in cur]
        result = items

        cache_set_json(cache_key, result, ttl=45)
        return jsonify(result)
