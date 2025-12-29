import os
import uuid
from fastapi import UploadFile
import boto3
from botocore.config import Config
from botocore.exceptions import NoCredentialsError, ClientError
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

# Initialize S3 client lazily to avoid errors if credentials aren't available at import time
_s3_client: Optional[boto3.client] = None

def get_s3_client():
    """Get or create S3 client instance with Signature Version 4"""
    global _s3_client
    if _s3_client is None:
        if not AWS_ACCESS_KEY_ID or not AWS_SECRET_ACCESS_KEY:
            raise Exception("AWS credentials not configured. Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables.")
        # Get AWS region from environment or default to eu-north-1
        aws_region = os.getenv("AWS_REGION", "eu-north-1")
        # Configure to use Signature Version 4 (AWS4-HMAC-SHA256)
        s3_config = Config(
            signature_version='s3v4',
            region_name=aws_region
        )
        _s3_client = boto3.client(
            "s3",
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=aws_region,
            config=s3_config
        )
    return _s3_client

def save_attachment(file: UploadFile, path_prefix: str) -> str:
    """Saves an attachment to S3 and returns the file key."""
    if not S3_BUCKET_NAME:
        raise Exception("S3_BUCKET_NAME environment variable is not set")
    
    try:
        s3 = get_s3_client()
        file_extension = os.path.splitext(file.filename)[1]
        file_name = f"{uuid.uuid4()}{file_extension}"
        file_key = os.path.join(path_prefix, file_name)

        s3.upload_fileobj(file.file, S3_BUCKET_NAME, file_key)

        return file_key
    except NoCredentialsError:
        raise Exception("AWS credentials not available")
    except Exception as e:
        raise Exception(f"Failed to upload to S3: {str(e)}")


def get_attachment_url(file_key: str, expiration: int = 3600, inline: bool = True):
    """Generates a presigned URL for an S3 object.
    
    Args:
        file_key: The S3 key of the file
        expiration: URL expiration time in seconds (default: 3600)
        inline: If True, sets ResponseContentDisposition to 'inline' for previewing.
                If False, sets it to 'attachment' for downloading (default: True)
    """
    if not S3_BUCKET_NAME or not file_key:
        return None
    try:
        s3 = get_s3_client()
        params = {
            "Bucket": S3_BUCKET_NAME,
            "Key": file_key
        }
        
        # Set Content-Disposition header to inline for previewing, or attachment for downloading
        if inline:
            params["ResponseContentDisposition"] = "inline"
        else:
            params["ResponseContentDisposition"] = "attachment"
        
        url = s3.generate_presigned_url(
            "get_object",
            Params=params,
            ExpiresIn=expiration,
        )
        return url
    except Exception:
        return None

def get_attachment(file_key: str):
    """Retrieves an attachment from S3."""
    if not S3_BUCKET_NAME:
        raise Exception("S3_BUCKET_NAME environment variable is not set")
    
    try:
        s3 = get_s3_client()
        if not file_key:
            raise ValueError("File key is required")
        response = s3.get_object(Bucket=S3_BUCKET_NAME, Key=file_key)
        if "Body" not in response:
            raise ValueError("No body in S3 response")
        return response["Body"]
    except NoCredentialsError:
        raise Exception("AWS credentials not available")
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        if error_code == 'NoSuchKey':
            raise Exception(f"File not found in S3: {file_key}")
        raise Exception(f"S3 error: {str(e)}")
    except Exception as e:
        raise Exception(f"Failed to retrieve attachment from S3: {str(e)}")


