import json
import tempfile
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from export_web import build_payload

ROOT = Path(__file__).resolve().parent / "website"
app = Flask(__name__, static_folder=str(ROOT), static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB


@app.get("/")
def index():
    return send_from_directory(ROOT, "index.html")


@app.post("/api/upload")
def upload():
    f = request.files.get("file")
    if not f or not f.filename.lower().endswith(".csv"):
        return jsonify(error="Sirf .csv file upload karo."), 400

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "upload.csv"
        f.save(path)
        try:
            payload = build_payload(path)
        except Exception as exc:  # column missing, dataset chhota, etc.
            return jsonify(error=str(exc)), 400

    return app.response_class(json.dumps(payload), mimetype="application/json")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)