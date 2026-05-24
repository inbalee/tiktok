from pathlib import Path
import os

import yaml
from flask import Flask, jsonify, render_template, request

from api_responses import api_error, api_success
from request_queue import QueueFullError, QueueTimeoutError, get_request_queue
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
request_queue = get_request_queue()


def _queue_error_response(exc: Exception):
    retry_after = os.environ.get("QUEUE_RETRY_AFTER_SEC", "5")
    return api_error(str(exc), 503, {"Retry-After": retry_after})


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


@app.route("/api/queue")
def api_queue_status():
    return api_success(request_queue.stats())


@app.route("/api/user/<username>")
def api_user(username: str):
    username = username.strip().lstrip("@")
    if not username:
        return api_error("Username is required", 400)

    try:
        data = request_queue.run(lambda: get_user_info(username))
        return api_success(data)
    except (QueueFullError, QueueTimeoutError) as exc:
        return _queue_error_response(exc)
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
        data = request_queue.run(lambda: search_by_keyword(keyword))
        return api_success(data)
    except (QueueFullError, QueueTimeoutError) as exc:
        return _queue_error_response(exc)
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
        data = request_queue.run(
            lambda: get_video_comments(video_id, cursor=cursor, count=count)
        )
        return api_success(data)
    except (QueueFullError, QueueTimeoutError) as exc:
        return _queue_error_response(exc)
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
        data = request_queue.run(lambda: get_video_metadata(video_url))
        return api_success(data)
    except (QueueFullError, QueueTimeoutError) as exc:
        return _queue_error_response(exc)
    except TikTokVideoNotFoundError as exc:
        return api_error(str(exc), 404)
    except TikTokFetchError as exc:
        return api_error(str(exc), 502)
    except Exception:
        return api_error("An unexpected error occurred", 500)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug, host="0.0.0.0", port=port)
