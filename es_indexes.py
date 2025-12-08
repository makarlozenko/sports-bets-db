from flask import Blueprint, jsonify
from elasticsearch_client import es

es_bp = Blueprint("es_indexes", __name__)

# -----------------------------------------------------------
# 1) INDEX DEFINITIONS
# -----------------------------------------------------------

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

# -----------------------------------------------------------
# DELETE INDEXES
# -----------------------------------------------------------

def delete_all_indexes():
    """Removes the project’s ES indexes."""
    if es.indices.exists(index=MATCHES_INDEX):
        es.indices.delete(index=MATCHES_INDEX)
    if es.indices.exists(index=BETS_INDEX):
        es.indices.delete(index=BETS_INDEX)

# -----------------------------------------------------------
# 2) /es/init
# -----------------------------------------------------------

@es_bp.route("/es/init", methods=["POST"])
def initialize_indexes():

    if not es.indices.exists(index=MATCHES_INDEX):
        es.indices.create(index=MATCHES_INDEX, body=MATCHES_MAPPING)

    if not es.indices.exists(index=BETS_INDEX):
        es.indices.create(index=BETS_INDEX, body=BETS_MAPPING)

    return jsonify({
        "status": "ok",
        "indexes": {
            MATCHES_INDEX: "ready",
            BETS_INDEX: "ready"
        }
    }), 200
