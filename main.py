# main.py
import os
import gevent.monkey
gevent.monkey.patch_all()

import certifi
from flask import Flask
from pymongo import MongoClient
from elasticsearch_client import es, test_es_connection

app = Flask(__name__)
test_es_connection()

# ---- MongoDB ----
client = MongoClient(
    'mongodb+srv://arinatichonovskaja_db_user:Komanda@sportbet.wafmb2f.mongodb.net/?retryWrites=true&w=majority&appName=SportBet',
    tlsCAFile=certifi.where()
)
db = client.SportBET
app.db = db

# ---- Routes ----
from matches import register_matches_routes
register_matches_routes(app, db)

from teams import register_teams_routes
register_teams_routes(app, db)

from bets import register_bets_routes
register_bets_routes(app, db)

from user import register_users_routes
register_users_routes(app, db)

from cart import register_cart_routes
register_cart_routes(app, db)

from chat import register_chat_routes
register_chat_routes(app, db)

# ---- Neo4j ----
from neo4j_connect import neo4j
neo4j(app, db)

from neo4j_endpoints import register_neo4j_routes
register_neo4j_routes(app)

from neo4j_endpoints import register_neo4j_rivalry_routes
register_neo4j_rivalry_routes(app)

from neo4j_endpoints import register_neo4j_recommendation_routes
register_neo4j_recommendation_routes(app)


from es_routes import register_es_routes
register_es_routes(app)

# ---- ES INIT ROUTES ----
from es_init import es_bp
app.register_blueprint(es_bp)

# ---- Run ----
if __name__ == "__main__":
    app.run(debug=True, threaded=True, host="127.0.0.1", port=5000)
