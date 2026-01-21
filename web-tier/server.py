import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, jsonify, abort
import time
import uuid
from werkzeug.utils import secure_filename
from botocore.exceptions import ClientError

from core.config import config
from core.aws_clients import get_s3_client
from core.sqs_helpers import send_message

app = Flask(__name__)

ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}


def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def check_result(job_id: str) -> str | None:
    s3 = get_s3_client()
    try:
        resp = s3.get_object(Bucket=config.s3_out_bucket, Key=job_id)
        return resp["Body"].read().decode("utf-8")
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            return None
        raise


@app.route('/', methods=['POST'])
def upload():
    if 'inputFile' not in request.files:
        return jsonify({"error": "No inputFile in request"}), 400

    file = request.files['inputFile']
    if not file or not file.filename:
        return jsonify({"error": "Empty filename"}), 400

    filename = secure_filename(file.filename)
    if not filename:
        return jsonify({"error": "Invalid filename"}), 400

    if not allowed_file(filename):
        return jsonify({"error": f"File type not allowed. Use: {ALLOWED_EXTENSIONS}"}), 400

    file.seek(0, 2)  #get file size
    size_mb = file.tell() / (1024 * 1024)
    file.seek(0)
    if size_mb > config.max_file_mb:
        return jsonify({"error": f"File too large. Max {config.max_file_mb}MB"}), 400

    job_id = str(uuid.uuid4())
    object_key = f"{job_id}_{filename}"

    s3 = get_s3_client()
    try:
        s3.upload_fileobj(file, config.s3_in_bucket, object_key)
    except Exception as e:
        return jsonify({"error": f"S3 upload failed: {str(e)}"}), 500

    try:
        send_message(config.sqs_req_queue_name, object_key)
    except Exception as e:
        return jsonify({"error": f"Failed to queue job: {str(e)}"}), 500

    #poll S3 for result instead of response queue (avoids race condition with concurrent requests)
    deadline = time.time() + config.max_wait_seconds
    while time.time() < deadline:
        result = check_result(job_id)
        if result is not None:
            return jsonify({
                "job_id": job_id,
                "status": "done",
                "result": result
            }), 200
        time.sleep(config.poll_interval)

    return jsonify({
        "job_id": job_id,
        "status": "pending"
    }), 202


@app.route('/status/<job_id>', methods=['GET'])
def status(job_id: str):
    result = check_result(job_id)
    if result is not None:
        return jsonify({
            "job_id": job_id,
            "status": "done",
            "result": result
        }), 200
    return jsonify({
        "job_id": job_id,
        "status": "pending"
    }), 202


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"}), 200


if __name__ == '__main__':
    app.run(threaded=True, debug=True, port=8000, host='0.0.0.0')
