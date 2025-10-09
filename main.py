# main.py
import os
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

if __name__ == "__main__":
    # paleidimas lokaliai
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)