import boto3
from functools import lru_cache
from core.config import config


@lru_cache(maxsize=1)
def get_s3_client():
    return boto3.client(
        "s3",
        region_name=config.aws_region,
        endpoint_url=config.aws_endpoint_url,
        aws_access_key_id=config.aws_access_key_id,
        aws_secret_access_key=config.aws_secret_access_key,
    )


@lru_cache(maxsize=1)
def get_sqs_client():
    return boto3.client(
        "sqs",
        region_name=config.aws_region,
        endpoint_url=config.aws_endpoint_url,
        aws_access_key_id=config.aws_access_key_id,
        aws_secret_access_key=config.aws_secret_access_key,
    )
