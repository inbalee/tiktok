from flask import jsonify


def api_success(data, status: int = 200):
    return jsonify({"success": True, "data": data}), status


def api_error(message: str, status: int = 400):
    return jsonify({"success": False, "error": message}), status
