

    # ---------- UPDATE STATUS ----------
    @app.post("/bets/update_status")
    def update_bet_status():
        data = request.get_json(silent=True) or {}
        bet_id = data.get("betId")
        status = data.get("status")
        if not bet_id or not status:
            return jsonify({"error": "Missing betId or status"}), 400
        oid = to_oid(bet_id)
        if not oid:
            return jsonify({"error": "Invalid betId"}), 400
        res = BETS.update_one({"_id": oid}, {"$set": {"status": status}})
        if res.modified_count == 0:
            return jsonify({"error": "No bet updated"}), 404
        return jsonify({"message": "Bet status updated", "betId": bet_id, "status": status})
