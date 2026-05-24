from pathlib import Path

import yaml
from flask import Flask, jsonify, render_template, request

from api_responses import api_error, api_success
from tiktok_service import (
    TikTokCommentsNotFoundError,
    TikTokFetchError,
    TikTokSearchNotFoundError,
    TikTokUserNotFoundError,
    TikTokVideoNotFoundError,
    get_user_info,
    get_video_comments,
    get_video_metadata,
    search_by_keyword,
)

app = Flask(__name__)
OPENAPI_PATH = Path(__file__).with_name("openapi.yaml")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/docs")
def docs():
    return render_template("docs.html")


@app.route("/openapi.json")
def openapi_spec():
    with OPENAPI_PATH.open(encoding="utf-8") as spec_file:
        return jsonify(yaml.safe_load(spec_file))


@app.route("/api/user/<username>")
def api_user(username: str):
    username = username.strip().lstrip("@")
    if not username:
        return api_error("Username is required", 400)

    try:
        return api_success(get_user_info(username))
    except TikTokUserNotFoundError as exc:
        return api_error(str(exc), 404)
    except TikTokFetchError as exc:
        return api_error(str(exc), 502)
    except Exception:
        return api_error("An unexpected error occurred", 500)


@app.route("/api/search")
def api_search():
    keyword = request.args.get("q", "").strip()
    if not keyword:
        return api_error("Keyword is required", 400)

    try:
        return api_success(search_by_keyword(keyword))
    except TikTokSearchNotFoundError as exc:
        return api_error(str(exc), 404)
    except TikTokFetchError as exc:
        return api_error(str(exc), 502)
    except Exception:
        return api_error("An unexpected error occurred", 500)


@app.route("/api/video/<video_id>/comments")
def api_video_comments(video_id: str):
    cursor = request.args.get("cursor", 0, type=int)
    count = request.args.get("count", 50, type=int)

    try:
        return api_success(get_video_comments(video_id, cursor=cursor, count=count))
    except TikTokCommentsNotFoundError as exc:
        return api_error(str(exc), 404)
    except TikTokFetchError as exc:
        return api_error(str(exc), 502)
    except Exception:
        return api_error("An unexpected error occurred", 500)


@app.route("/api/video/metadata")
def api_video_metadata():
    video_url = request.args.get("url", "").strip()
    if not video_url:
        return api_error("Video link is required", 400)

    try:
        return api_success(get_video_metadata(video_url))
    except TikTokVideoNotFoundError as exc:
        return api_error(str(exc), 404)
    except TikTokFetchError as exc:
        return api_error(str(exc), 502)
    except Exception:
        return api_error("An unexpected error occurred", 500)


if __name__ == "__main__":
    app.run(debug=True, port=5001)
