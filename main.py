# main.py
import os
import gevent.monkey
gevent.monkey.patch_all()

import certifi
from datetime import datetime
from flask import Flask, request, jsonify
from pymongo import MongoClient
from bson import ObjectId

app = Flask(__name__)

client = MongoClient('mongodb+srv://arinatichonovskaja_db_user:Komanda@sportbet.wafmb2f.mongodb.net/?retryWrites=true&w=majority&appName=SportBet',
                     tlsCAFile=certifi.where())
db = client.SportBET        # DB pavadinimas

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

from neo4j_connect import neo4j
neo4j(app, db)

if __name__ == "__main__":
    # paleidimas lokaliai
    app.run(debug=True, threaded=True, host="127.0.0.1", port=5000)# main.py
import os
import gevent.monkey
gevent.monkey.patch_all()

import certifi
from datetime import datetime
from flask import Flask, request, jsonify
from pymongo import MongoClient
from bson import ObjectId

app = Flask(__name__)

client = MongoClient('mongodb+srv://arinatichonovskaja_db_user:Komanda@sportbet.wafmb2f.mongodb.net/?retryWrites=true&w=majority&appName=SportBet',
                     tlsCAFile=certifi.where())
db = client.SportBET        # DB pavadinimas

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

from neo4j_connect import neo4j
neo4j(app, db)

if __name__ == "__main__":
    # paleidimas lokaliai
    app.run(debug=True, threaded=True, host="127.0.0.1", port=5000)