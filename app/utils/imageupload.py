from fastapi import UploadFile, HTTPException
import boto3
from botocore.exceptions import ClientError
import uuid
import os
from dotenv import load_dotenv  # pip install python-dotenv if not installed

# Load environment variables at the start
load_dotenv()

# Retrieve configs (these will now pull from your .env)
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "imagestore")
S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL")
AWS_REGION = os.getenv("AWS_REGION", "auto")

# Check if required creds are set
if not R2_ACCESS_KEY_ID or not R2_SECRET_ACCESS_KEY or not S3_ENDPOINT_URL:
    raise ValueError("Missing required environment variables for R2 access. Check your .env file.")

# Initialize S3 client for R2
s3_client = boto3.client(
    "s3",
    aws_access_key_id=R2_ACCESS_KEY_ID,
    aws_secret_access_key=R2_SECRET_ACCESS_KEY,
    endpoint_url=S3_ENDPOINT_URL,
    region_name=AWS_REGION
)

def save_uploaded_image(upload_file: UploadFile, folder: str = "static") -> str:
    """
    Utility function to upload an image to Cloudflare R2 and return its public URL.
    (Same as before; no changes needed here.)
    """
    # Validate that it's an image
    if not upload_file.content_type or not upload_file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Uploaded file must be an image")

    # Generate a unique key
    file_extension = upload_file.filename.split('.')[-1] if '.' in upload_file.filename else ''
    unique_key = f"{folder}/{uuid.uuid4()}.{file_extension}"

    # Upload to R2
    try:
        upload_file.file.seek(0)
        s3_client.upload_fileobj(
            upload_file.file,
            S3_BUCKET_NAME,
            unique_key,
            ExtraArgs={"ContentType": upload_file.content_type}
        )
    except ClientError as e:
        raise HTTPException(status_code=500, detail=f"Error uploading to R2: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

    # Public URL
    image_url = f"{S3_ENDPOINT_URL}/{S3_BUCKET_NAME}/{unique_key}"
    return image_url