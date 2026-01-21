import os
from dataclasses import dataclass
from typing import Optional


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, str(default)))
    except ValueError:
        return default


@dataclass(frozen=True)
class Config:
    aws_region: str
    aws_endpoint_url: Optional[str]
    aws_access_key_id: str
    aws_secret_access_key: str

    s3_in_bucket: str
    s3_out_bucket: str

    sqs_req_queue_name: str
    sqs_resp_queue_name: str

    sqs_max_receive_count: int
    sqs_visibility_timeout: int
    sqs_wait_time: int

    max_wait_seconds: int
    poll_interval: float

    max_file_mb: int


def load_config() -> Config:
    endpoint = _env("AWS_ENDPOINT_URL")
    return Config(
        aws_region=_env("AWS_REGION", "us-east-1"),
        aws_endpoint_url=endpoint if endpoint else None,
        aws_access_key_id=_env("AWS_ACCESS_KEY_ID", "test"),
        aws_secret_access_key=_env("AWS_SECRET_ACCESS_KEY", "test"),

        s3_in_bucket=_env("S3_IN_BUCKET", "input-bucket"),
        s3_out_bucket=_env("S3_OUT_BUCKET", "output-bucket"),

        sqs_req_queue_name=_env("SQS_REQ_QUEUE_NAME", "request-queue"),
        sqs_resp_queue_name=_env("SQS_RESP_QUEUE_NAME", "response-queue"),

        sqs_max_receive_count=_env_int("SQS_MAX_RECEIVE_COUNT", 5),
        sqs_visibility_timeout=_env_int("SQS_VISIBILITY_TIMEOUT_SECONDS", 60),
        sqs_wait_time=_env_int("SQS_WAIT_TIME_SECONDS", 10),

        max_wait_seconds=_env_int("MAX_WAIT_SECONDS", 30),
        poll_interval=float(_env("POLL_INTERVAL_SECONDS", "1")),

        max_file_mb=_env_int("MAX_FILE_MB", 8),
    )


config = load_config()
