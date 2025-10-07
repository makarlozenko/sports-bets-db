# main.py
import os
import certifi
from datetime import datetime
from flask import Flask, request, jsonify
from pymongo import MongoClient
from bson import ObjectId

app = Flask(__name__)

# TAVO Atlas prisijungimas (kaip davei)
client = MongoClient('mongodb+srv://arinatichonovskaja_db_user:Komanda@sportbet.wafmb2f.mongodb.net/?retryWrites=true&w=majority&appName=SportBet',
                     tlsCAFile=certifi.where())
db = client.SportBET        # DB pavadinimas
TEAMS = db.Team             # Kolekcija

def to_oid(s):
    try:
        return ObjectId(s)
    except Exception:
        return None

def ser(doc):
    if not doc:
        return None
    d = dict(doc)
    if isinstance(d.get("_id"), ObjectId):
        d["_id"] = str(d["_id"])
    return d

@app.get("/health")
def health():
    return jsonify({"ok": True, "db": "SportBET", "collections": db.list_collection_names()})

# LIST
@app.get("/teams")
def list_teams():
    limit = min(int(request.args.get("limit", 20)), 200)
    skip = max(int(request.args.get("skip", 0)), 0)
    cur = TEAMS.find({})
    items = [ser(x) for x in cur.skip(skip).limit(limit)]
    total = TEAMS.count_documents({})
    return jsonify({"items": items, "total": total, "limit": limit, "skip": skip})

# CREATE
@app.post("/teams")
def create_team():
    data = request.get_json(silent=True) or {}
    now = datetime.utcnow()
    data.setdefault("created_at", now)
    data.setdefault("updated_at", now)
    res = TEAMS.insert_one(data)
    return jsonify(ser(TEAMS.find_one({"_id": res.inserted_id}))), 201

# READ (by id)
@app.get("/teams/<id>")
def get_team(id):
    oid = to_oid(id)
    if not oid:
        return jsonify({"error": "Invalid id"}), 400
    doc = TEAMS.find_one({"_id": oid})
    if not doc:
        return jsonify({"error": "Not found"}), 404
    return jsonify(ser(doc))

# UPDATE (partial)
@app.patch("/teams/<id>")
def update_team(id):
    oid = to_oid(id)
    if not oid:
        return jsonify({"error": "Invalid id"}), 400
    data = request.get_json(silent=True) or {}
    data["updated_at"] = datetime.utcnow()
    upd = TEAMS.update_one({"_id": oid}, {"$set": data})
    if not upd.matched_count:
        return jsonify({"error": "Not found"}), 404
    return jsonify(ser(TEAMS.find_one({"_id": oid})))

# DELETE
@app.delete("/teams/<id>")
def delete_team(id):
    oid = to_oid(id)
    if not oid:
        return jsonify({"error": "Invalid id"}), 400
    res = TEAMS.delete_one({"_id": oid})
    if not res.deleted_count:
        return jsonify({"error": "Not found"}), 404
    return jsonify({"deleted": True, "_id": id})

from bets import register_bets_routes
register_bets_routes(app, db)

from user import register_users_routes
register_users_routes(app, db)

if __name__ == "__main__":
    # paleidimas lokaliai
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)
