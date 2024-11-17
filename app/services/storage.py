from botocore.config import Config
import boto3
import logging
from app.core.config import get_settings

settings = get_settings()


class S3Service:
    def __init__(self):
        self.client = self._initialize_client()

    def _initialize_client(self):
        try:
            client = boto3.client(
                "s3",
                aws_access_key_id=settings.AWS_ACCESS_KEY,
                aws_secret_access_key=settings.AWS_SECRET_KEY,
                config=Config(
                    signature_version="s3v4", region_name=settings.AWS_REGION
                ),
            )
            client.head_bucket(Bucket=settings.S3_BUCKET)
            return client
        except Exception as e:
            logging.error(f"S3 initialization error: {e}")
            raise Exception(f"Failed to initialize S3: {str(e)}")

    async def upload_file(
        self, key: str, data: bytes, content_type: str = "image/jpeg"
    ):
        try:
            self.client.put_object(
                Bucket=settings.S3_BUCKET, Key=key, Body=data, ContentType=content_type
            )
            return f"https://{settings.S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"
        except Exception as e:
            logging.error(f"S3 upload error: {e}")
            raise Exception(f"Failed to upload to S3: {str(e)}")
