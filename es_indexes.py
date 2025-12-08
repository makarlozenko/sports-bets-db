from elasticsearch_client import es

MATCHES_INDEX = "matches_search"
BETS_INDEX = "bets_analytics"


# ============================
# Check existing index
# ============================
def index_exists(index_name):
    return es.indices.exists(index=index_name)


# ============================
# Create index matches_search
# ============================
def create_matches_index():
    if index_exists(MATCHES_INDEX):
        return {"status": "exists"}

    body = {
        "mappings": {
            "properties": {
                "match_id": {"type": "keyword"},
                "team1": {"type": "text"},
                "team2": {"type": "text"},
                "sport": {"type": "keyword"},
                "date": {"type": "date"},
                "status": {"type": "keyword"}
            }
        }
    }

    es.indices.create(index=MATCHES_INDEX, body=body)
    return {"status": "created"}


# ============================
# Create index bets_analytics
# ============================
def create_bets_index():
    if index_exists(BETS_INDEX):
        return {"status": "exists"}

    body = {
        "mappings": {
            "properties": {
                "bet_id": {"type": "keyword"},
                "userEmail": {"type": "keyword"},
                "stake": {"type": "float"},
                "choice": {"type": "keyword"},
                "status": {"type": "keyword"},
                "team": {"type": "keyword"},
                "createdAt": {"type": "date"}
            }
        }
    }

    es.indices.create(index=BETS_INDEX, body=body)
    return {"status": "created"}


# ============================
# Delete all indexes ES
# ============================
def delete_all_indexes():
    if index_exists(MATCHES_INDEX):
        es.indices.delete(index=MATCHES_INDEX)

    if index_exists(BETS_INDEX):
        es.indices.delete(index=BETS_INDEX)

    return {"deleted": True}


# ============================
# Create all indexes
# ============================
def init_all_indexes():
    result = {
        "matches": create_matches_index(),
        "bets": create_bets_index()
    }
    return result
