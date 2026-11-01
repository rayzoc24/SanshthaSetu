"""
Storage Service for SanshthaSetu.
Supports S3-compatible object storage (Neon Object Storage / Cloudflare R2 / AWS S3).
"""

from __future__ import annotations

import io
from typing import BinaryIO, Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.config import settings


def get_s3_client():
    """Return a configured boto3 S3 client with standard SigV4."""
    if not settings.aws_endpoint_url_s3:
        raise ValueError("Storage configuration error: AWS_ENDPOINT_URL_S3 is not set.")

    return boto3.client(
        "s3",
        endpoint_url=settings.aws_endpoint_url_s3,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        region_name=settings.aws_region,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


class StorageService:
    def __init__(self, bucket_name: Optional[str] = None):
        self.bucket_name = bucket_name or settings.neon_storage_bucket

    def upload_file(
        self,
        file_obj: BinaryIO | bytes,
        object_key: str,
        content_type: str = "application/pdf",
    ) -> str:
        """
        Upload an object to storage and return its object key.
        """
        s3 = get_s3_client()
        if isinstance(file_obj, bytes):
            body = io.BytesIO(file_obj)
        else:
            body = file_obj

        extra_args = {"ContentType": content_type}
        s3.upload_fileobj(body, self.bucket_name, object_key, ExtraArgs=extra_args)
        return object_key

    def generate_signed_url(self, object_key: str, expires_in: int = 3600) -> str:
        """
        Generate a presigned GET URL for an object (never stored in the database).
        """
        s3 = get_s3_client()
        return s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket_name, "Key": object_key},
            ExpiresIn=expires_in,
        )

    def delete_file(self, object_key: str) -> bool:
        """
        Delete an object from storage.
        """
        s3 = get_s3_client()
        try:
            s3.delete_object(Bucket=self.bucket_name, Key=object_key)
            return True
        except ClientError:
            return False

    def get_file_bytes(self, object_key: str) -> bytes:
        """
        Download object bytes into memory.
        """
        s3 = get_s3_client()
        response = s3.get_object(Bucket=self.bucket_name, Key=object_key)
        return response["Body"].read()


storage_service = StorageService()

