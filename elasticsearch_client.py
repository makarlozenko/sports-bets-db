from elasticsearch import Elasticsearch

# Important: official 8.x client requires dict, not string
es = Elasticsearch(
    hosts=[{"host": "localhost", "port": 9200, "scheme": "http"}],
    verify_certs=False
)

def test_es_connection():
    try:
        info = es.info()
        print("Elasticsearch is UP")
        print("Cluster:", info['cluster_name'])
        print("Version:", info['version']['number'])
    except Exception as e:
        print("Elasticsearch is DOWN")
        print("ERROR:", e)
