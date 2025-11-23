import logging
import uuid
from pathlib import Path

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.core.config import settings

logger = logging.getLogger(__name__)


class S3Service:
    """Service for handling S3/MinIO operations."""

    def __init__(self):
        """Initialize S3 client."""
        self.bucket_name = settings.S3_BUCKET_NAME
        self.client = boto3.client(
            's3',
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
            region_name=settings.S3_REGION,
            use_ssl=settings.S3_USE_SSL,
            config=Config(signature_version='s3v4'),
        )
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self) -> None:
        """Ensure the bucket exists, create it if it doesn't."""
        try:
            self.client.head_bucket(Bucket=self.bucket_name)
            logger.debug(f'S3 bucket {self.bucket_name} already exists')
        except ClientError as e:
            # Bucket doesn't exist, create it
            error_code = e.response.get('Error', {}).get('Code', '')
            http_status = e.response.get('ResponseMetadata', {}).get('HTTPStatusCode', 0)

            if error_code not in ('404', 'NoSuchBucket') and http_status != 404:
                # Other ClientError (e.g., connection error, permission denied)
                logger.warning(
                    f'Error checking S3 bucket {self.bucket_name}: {error_code}. Error: {e}',
                )
                raise

            logger.info(f'Creating S3 bucket {self.bucket_name}')
            try:
                if settings.S3_ENDPOINT_URL:
                    self.client.create_bucket(Bucket=self.bucket_name)
                elif settings.S3_REGION == 'us-east-1':
                    # AWS S3 - may need location constraint (except for us-east-1)
                    self.client.create_bucket(Bucket=self.bucket_name)
                else:
                    self.client.create_bucket(
                        Bucket=self.bucket_name,
                        CreateBucketConfiguration={'LocationConstraint': settings.S3_REGION},
                    )
                logger.info(f'Successfully created S3 bucket {self.bucket_name}')
            except ClientError as create_error:
                # Bucket might have been created by another process
                create_error_code = create_error.response.get('Error', {}).get('Code', '')
                if create_error_code in ('BucketAlreadyOwnedByYou', 'BucketAlreadyExists'):
                    logger.debug(f'S3 bucket {self.bucket_name} was created by another process')
                else:
                    logger.error(
                        f'Failed to create S3 bucket {self.bucket_name}: {create_error}',
                        exc_info=True,
                    )
                    raise
        except Exception as e:
            # Unexpected errors (network issues, etc.)
            logger.error(
                f'Unexpected error ensuring S3 bucket exists: {e}',
                exc_info=True,
            )
            raise

    def upload_file(self, file_content: bytes, file_key: str, content_type: str | None = None) -> str:
        """
        Upload a file to S3.

        :param file_content: The file content as bytes
        :param file_key: The S3 key (path) for the file
        :param content_type: Optional content type (MIME type)
        :return: The S3 key of the uploaded file
        :raises ClientError: If the upload fails
        """
        extra_args = {}
        if content_type:
            extra_args['ContentType'] = content_type

        try:
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=file_key,
                Body=file_content,
                **extra_args,
            )
            logger.debug(f'Successfully uploaded file to S3: {file_key}')
            return file_key
        except ClientError as e:
            logger.error(
                f'Failed to upload file to S3: {file_key}. Error: {e}',
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(
                f'Unexpected error uploading file to S3: {file_key}. Error: {e}',
                exc_info=True,
            )
            raise

    def delete_file(self, file_key: str) -> None:
        """
        Delete a file from S3.

        :param file_key: The S3 key (path) of the file to delete
        """
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=file_key)
            logger.debug(f'Successfully deleted file from S3: {file_key}')
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == 'NoSuchKey':
                # File doesn't exist - this is acceptable, log at debug level
                logger.debug(f'File not found in S3 (may have been already deleted): {file_key}')
            else:
                # Other errors (permission denied, etc.) should be logged
                logger.warning(
                    f'Error deleting file from S3: {file_key}. Error code: {error_code}. Error: {e}',
                )
        except Exception as e:
            logger.error(
                f'Unexpected error deleting file from S3: {file_key}. Error: {e}',
                exc_info=True,
            )
            # Don't raise - deletion failures shouldn't break the application flow

    def get_presigned_url(self, file_key: str, expiration: int = 3600) -> str:
        """
        Generate a presigned URL for accessing a file.

        :param file_key: The S3 key (path) of the file
        :param expiration: URL expiration time in seconds (default: 1 hour)
        :return: Presigned URL, or empty string if generation fails
        """
        try:
            url = self.client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': file_key},
                ExpiresIn=expiration,
            )
            logger.debug(f'Generated presigned URL for S3 file: {file_key}')
            return url
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            logger.warning(
                f'Failed to generate presigned URL for S3 file: {file_key}. Error code: {error_code}. Error: {e}',
            )
            return ''
        except Exception as e:
            logger.error(
                f'Unexpected error generating presigned URL for S3 file: {file_key}. Error: {e}',
                exc_info=True,
            )
            return ''

    def file_exists(self, file_key: str) -> bool:
        """
        Check if a file exists in S3.

        :param file_key: The S3 key (path) of the file
        :return: True if file exists, False otherwise
        """
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=file_key)
            return True
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == '404':
                # File doesn't exist - this is expected, no need to log
                return False
            else:
                # Other errors (permission denied, etc.) should be logged
                logger.warning(
                    f'Error checking if file exists in S3: {file_key}. Error code: {error_code}. Error: {e}',
                )
                return False
        except Exception as e:
            logger.error(
                f'Unexpected error checking if file exists in S3: {file_key}. Error: {e}',
                exc_info=True,
            )
            return False


def generate_image_key(cookbook_id: uuid.UUID, image_type: str, extension: str = 'jpg') -> str:
    """
    Generate a unique S3 key for a cookbook image.

    :param cookbook_id: The cookbook UUID
    :param image_type: Type of image ('cover' or 'thumbnail')
    :param extension: File extension (default: 'jpg')
    :return: S3 key path
    """
    unique_id = uuid.uuid4()
    return f'cookbooks/{cookbook_id}/{image_type}-{unique_id}.{extension}'


def get_file_extension(filename: str) -> str:
    """
    Extract file extension from filename.

    :param filename: The filename
    :return: File extension (without dot)
    """
    return Path(filename).suffix.lstrip('.').lower() or 'jpg'


# Global S3 service instance (lazy initialization)
_s3_service: S3Service | None = None


class _S3ServiceProxy:
    """Proxy class for lazy S3 service initialization."""

    def __getattr__(self, name: str):
        """Delegate attribute access to the actual S3 service."""
        service = _get_s3_service()
        return getattr(service, name)


def _get_s3_service() -> S3Service:
    """Get or create the global S3 service instance."""
    global _s3_service
    if _s3_service is None:
        _s3_service = S3Service()
    return _s3_service


# Global proxy instance for lazy initialization
s3_service = _S3ServiceProxy()
