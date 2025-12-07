from elasticsearch import Elasticsearch

ES_URL = "http://localhost:9200"

es = Elasticsearch(
    ES_URL,
    verify_certs=False
)

def test_es_connection():
    try:
        if es.ping():
            print("Elasticsearch is UP")
        else:
            print("Elasticsearch is DOWN")
    except Exception as e:
        print("ES CONNECTION ERROR:", e)
