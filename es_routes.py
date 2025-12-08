from flask import jsonify
from es_indexes import init_all_indexes, delete_all_indexes

def register_es_routes(app):

    @app.post("/es/init")
    def es_init():
        """
        Create all Elasticsearch indexes.
        """
        result = init_all_indexes()
        return jsonify({
            "status": "ok",
            "indexes": result
        }), 200


    @app.post("/es/reset")
    def es_reset():
        """
        Reset Elasticsearch by dropping and recreating indexes.
        """
        delete_all_indexes()
        result = init_all_indexes()

        return jsonify({
            "status": "reset_ok",
            "indexes": result
        }), 200
