from flask import jsonify


def api_success(data, status: int = 200):
    return jsonify({"success": True, "data": data}), status


def api_error(message: str, status: int = 400, headers: dict | None = None):
    response = jsonify({"success": False, "error": message})
    if headers:
        return response, status, headers
    return response, status
