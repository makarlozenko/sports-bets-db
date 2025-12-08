# es_init.py
from flask import Blueprint, jsonify
from elasticsearch_client import es

es_bp = Blueprint("es_init", __name__)

# ------------------------------------------------------
# 1. MATCHES_INDEX
# ------------------------------------------------------
MATCHES_INDEX = "matches_search"
MATCHES_MAPPING = {
    "mappings": {
        "properties": {
            "match_id": {"type": "keyword"},
            "sport": {"type": "keyword"},
            "team1": {"type": "text"},
            "team2": {"type": "text"},
            "matchType": {"type": "keyword"},
            "date": {"type": "date", "format": "yyyy-MM-dd"},
            "odds": {"type": "float"}
        }
    }
}

# ------------------------------------------------------
# 2. BETS_INDEX
# ------------------------------------------------------
BETS_INDEX = "bets_analytics"
BETS_MAPPING = {
    "mappings": {
        "properties": {
            "bet_id": {"type": "keyword"},
            "userEmail": {"type": "keyword"},
            "sport": {"type": "keyword"},
            "team": {"type": "keyword"},
            "choice": {"type": "keyword"},
            "stake": {"type": "float"},
            "status": {"type": "keyword"},
            "createdAt": {"type": "date"}
        }
    }
}

# ------------------------------------------------------
# API: /es/init
# ------------------------------------------------------
@es_bp.route("/es/init", methods=["POST", "GET"])
def init_es():
    try:
        # 1) Delete old indexes
        if es.indices.exists(index=MATCHES_INDEX):
            es.indices.delete(index=MATCHES_INDEX)

        if es.indices.exists(index=BETS_INDEX):
            es.indices.delete(index=BETS_INDEX)

        # 2) Create new indexes
        es.indices.create(index=MATCHES_INDEX, body=MATCHES_MAPPING)
        es.indices.create(index=BETS_INDEX, body=BETS_MAPPING)

        return jsonify({
            "message": "Elasticsearch indices created",
            "created": [MATCHES_INDEX, BETS_INDEX]
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
