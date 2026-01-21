from functools import lru_cache
from core.aws_clients import get_sqs_client
from core.config import config


@lru_cache(maxsize=10)
def get_queue_url(queue_name: str) -> str:
    sqs = get_sqs_client()
    resp = sqs.get_queue_url(QueueName=queue_name)
    return resp["QueueUrl"]


def send_message(queue_name: str, body: str) -> dict:
    sqs = get_sqs_client()
    url = get_queue_url(queue_name)
    return sqs.send_message(QueueUrl=url, MessageBody=body)


def receive_messages(
    queue_name: str,
    max_messages: int = 1,
    wait_time: int = None,
    visibility_timeout: int = None
) -> list:
    sqs = get_sqs_client()
    url = get_queue_url(queue_name)

    params = {
        "QueueUrl": url,
        "MaxNumberOfMessages": max_messages,
        "WaitTimeSeconds": wait_time if wait_time is not None else config.sqs_wait_time,
    }
    if visibility_timeout is not None:
        params["VisibilityTimeout"] = visibility_timeout

    resp = sqs.receive_message(**params)
    return resp.get("Messages", [])


def delete_message(queue_name: str, receipt_handle: str):
    sqs = get_sqs_client()
    url = get_queue_url(queue_name)
    sqs.delete_message(QueueUrl=url, ReceiptHandle=receipt_handle)


def change_visibility(queue_name: str, receipt_handle: str, timeout: int):
    sqs = get_sqs_client()
    url = get_queue_url(queue_name)
    sqs.change_message_visibility(
        QueueUrl=url,
        ReceiptHandle=receipt_handle,
        VisibilityTimeout=timeout
    )
