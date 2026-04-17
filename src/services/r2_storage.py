"""
Cloudflare R2 Storage Service.

Handles uploading audio files to R2 for public hosting.
R2 is S3-compatible, so we use boto3 with the R2 endpoint.

Free tier includes:
- 10GB storage
- 10M Class A operations (writes) per month
- 1M Class B operations (reads) per month
"""

from pathlib import Path

import boto3
from botocore.config import Config
from loguru import logger

from src.config import settings


class R2Storage:
    """Upload and manage files in Cloudflare R2."""

    def __init__(self):
        """Initialize R2 client with credentials from settings."""
        self.account_id = settings.r2_account_id
        self.access_key_id = settings.r2_access_key_id
        self.secret_access_key = settings.r2_secret_access_key
        self.bucket_name = settings.r2_bucket_name
        self.public_url = settings.r2_public_url

        self._client = None

    def is_configured(self) -> bool:
        """Check if R2 credentials are configured."""
        return all(
            [
                self.account_id,
                self.access_key_id,
                self.secret_access_key,
                self.public_url,
            ]
        )

    @property
    def client(self):
        """Lazy-initialize the S3 client for R2."""
        if self._client is None:
            if not self.is_configured():
                raise ValueError("R2 is not configured. Check R2_* settings in .env")

            endpoint_url = f"https://{self.account_id}.r2.cloudflarestorage.com"

            self._client = boto3.client(
                "s3",
                endpoint_url=endpoint_url,
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key,
                config=Config(
                    signature_version="s3v4",
                    retries={"max_attempts": 3, "mode": "standard"},
                ),
            )

        return self._client

    def upload_file(self, local_path: Path | str, key: str | None = None) -> str | None:
        """
        Upload a file to R2 and return its public URL.

        Args:
            local_path: Path to the local file to upload
            key: Object key (filename) in R2. Defaults to the local filename.

        Returns:
            Public URL of the uploaded file, or None if upload failed.
        """
        if not self.is_configured():
            logger.warning("R2 not configured - skipping upload")
            return None

        local_path = Path(local_path)
        if not local_path.exists():
            logger.error(f"File not found: {local_path}")
            return None

        # Default key is the filename
        if key is None:
            key = local_path.name

        try:
            # Upload with public-read ACL and correct content type
            content_type = (
                "audio/mpeg" if local_path.suffix == ".mp3" else "application/octet-stream"
            )

            self.client.upload_file(
                str(local_path),
                self.bucket_name,
                key,
                ExtraArgs={
                    "ContentType": content_type,
                },
            )

            # Construct public URL
            public_url = f"{self.public_url.rstrip('/')}/{key}"
            logger.debug(f"Uploaded {local_path.name} to R2: {public_url}")
            return public_url

        except Exception as e:
            logger.error(f"Failed to upload {local_path} to R2: {e}")
            return None

    def delete_file(self, key: str) -> bool:
        """
        Delete a file from R2.

        Args:
            key: Object key (filename) to delete

        Returns:
            True if deleted successfully, False otherwise.
        """
        if not self.is_configured():
            return False

        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=key)
            logger.debug(f"Deleted {key} from R2")
            return True
        except Exception as e:
            logger.error(f"Failed to delete {key} from R2: {e}")  # nosec B608
            return False

    def file_exists(self, key: str) -> bool:
        """
        Check if a file exists in R2.

        Args:
            key: Object key (filename) to check

        Returns:
            True if file exists, False otherwise.
        """
        if not self.is_configured():
            return False

        try:
            self.client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except Exception:
            return False


# Global instance for convenience
_r2_storage: R2Storage | None = None


def get_r2_storage() -> R2Storage:
    """Get the global R2Storage instance."""
    global _r2_storage
    if _r2_storage is None:
        _r2_storage = R2Storage()
    return _r2_storage
