import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import subprocess
import tempfile
import time
import random
from botocore.exceptions import ClientError

from core.config import config
from core.aws_clients import get_s3_client
from core.sqs_helpers import (
    receive_messages,
    delete_message,
    send_message,
    change_visibility,
)


def parse_job_id(object_key: str) -> tuple[str, str] | None:
    parts = object_key.split("_", 1)  #split once, filename may have underscores
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return None
    return parts[0], parts[1]


def run_face_recognition(image_path: str, timeout: int = 30) -> str:
    try:
        result = subprocess.run(
            ["python3", "face_recognition.py", image_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        return result.stdout.strip() or result.stderr.strip() or "UNKNOWN"
    except subprocess.TimeoutExpired:
        return "TIMEOUT"
    except Exception as e:
        return f"ERROR:{str(e)}"


def process_message(message: dict) -> bool:
    """Returns True to delete message, False to retry."""
    body = message.get("Body", "")
    receipt_handle = message["ReceiptHandle"]

    parsed = parse_job_id(body)
    if not parsed:
        print(f"Malformed message body, deleting: {body}")  #poison pill, delete it
        return True

    job_id, filename = parsed
    print(f"Processing job_id={job_id} filename={filename}")

    s3 = get_s3_client()
    tmp_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{filename}") as tmp:
            tmp_path = tmp.name
            try:
                s3.download_file(config.s3_in_bucket, body, tmp_path)
            except ClientError as e:
                if e.response["Error"]["Code"] == "NoSuchKey":
                    print(f"S3 object not found: {body}")
                    s3.put_object(Bucket=config.s3_out_bucket, Key=job_id, Body="NOT_FOUND")
                    return True
                raise

        result = run_face_recognition(tmp_path)
        print(f"Recognition result for {job_id}: {result}")

        s3.put_object(Bucket=config.s3_out_bucket, Key=job_id, Body=result)

        try:
            send_message(config.sqs_resp_queue_name, f"{body}:{result}")  #legacy/debug
        except Exception:
            pass

        return True

    except Exception as e:
        print(f"Error processing {job_id}: {e}")
        try:
            jitter = random.randint(5, 15)  #backoff with jitter
            change_visibility(config.sqs_req_queue_name, receipt_handle, jitter)
        except Exception:
            pass
        return False

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


def main():
    print("Worker started, polling request queue...")
    while True:
        try:
            messages = receive_messages(
                config.sqs_req_queue_name,
                max_messages=1,
                wait_time=config.sqs_wait_time,
                visibility_timeout=config.sqs_visibility_timeout
            )

            for msg in messages:
                should_delete = process_message(msg)
                if should_delete:
                    delete_message(config.sqs_req_queue_name, msg["ReceiptHandle"])

        except Exception as e:
            print(f"Queue poll error: {e}")
            time.sleep(5)


if __name__ == '__main__':
    main()
