import os
import uuid
import boto3
from boto3.s3.transfer import TransferConfig

AWS_REGION = os.getenv("AWS_REGION")
AWS_S3_BUCKET = os.getenv("AWS_S3_BUCKET")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

s3_client = boto3.client(
    "s3",
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)

config = TransferConfig(
    multipart_threshold=5 * 1024 * 1024,  # 5MB
    multipart_chunksize=5 * 1024 * 1024,  # 5MB per chunk
    max_concurrency=2,
    use_threads=True,
)

class S3Service:
    @staticmethod
    def generate_key(filename: str, folder: str = "vin-temp") -> str:
        ext = filename.split(".")[-1]
        unique = f"{uuid.uuid4().hex}.{ext}"
        return f"{folder}/{unique}"

    @staticmethod
    def upload_bytes(data: bytes, key: str, content_type: str = "image/png") -> str:
        """Upload image/PDF bytes to S3 (multipart-safe)"""
        s3_client.upload_fileobj(
            Fileobj=bytes_to_filelike(data),
            Bucket=AWS_S3_BUCKET,
            Key=key,
            ExtraArgs={"ContentType": content_type},
            Config=config,
        )
        return f"https://{AWS_S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{key}"

def bytes_to_filelike(data: bytes):
    import io
    return io.BytesIO(data)
