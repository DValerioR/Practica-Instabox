"""Utilidades para subir y bajar objetos de S3 usando el instance profile de la EC2."""

import os

import boto3

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

_s3_client = boto3.client("s3", region_name=AWS_REGION)


def upload_bytes(bucket: str, key: str, data: bytes, content_type: str = "image/jpeg") -> None:
    _s3_client.put_object(Bucket=bucket, Key=key, Body=data, ContentType=content_type)


def download_bytes(bucket: str, key: str) -> bytes:
    obj = _s3_client.get_object(Bucket=bucket, Key=key)
    return obj["Body"].read()