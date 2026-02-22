import logging
import os
import uuid

import boto3
from botocore.exceptions import ClientError

from src.config import MissingConfigError, get_aws_config

logger = logging.getLogger(__name__)


def get_s3_client():
    """
    boto3 S3 클라이언트를 생성해 반환합니다.
    """
    try:
        aws_config = get_aws_config()
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=aws_config["aws_access_key_id"],
            aws_secret_access_key=aws_config["aws_secret_access_key"],
            region_name=aws_config["aws_region_name"],
        )
        return s3_client
    except MissingConfigError:
        raise
    except Exception as e:
        logger.error("S3 클라이언트 생성 중 오류 발생: %s", e)
        return None


def upload_file_to_s3(uploaded_file):
    """
    업로드된 파일 객체를 S3에 직접 업로드합니다.
    성공 시 S3 객체 URL, 실패 시 None을 반환합니다.
    """
    s3_client = get_s3_client()
    if s3_client is None or uploaded_file is None:
        return None

    aws_config = get_aws_config()
    bucket_name = aws_config["aws_storage_bucket_name"]
    _, file_extension = os.path.splitext(uploaded_file.name)
    object_name = f"uploads/{uuid.uuid4()}{file_extension}"
    aws_region_name = aws_config["aws_region_name"]

    try:
        s3_client.upload_fileobj(
            uploaded_file,
            bucket_name,
            object_name,
            ExtraArgs={"ContentType": uploaded_file.type},
        )

        file_url = f"https://{bucket_name}.s3.{aws_region_name}.amazonaws.com/{object_name}"

        logger.info("'%s' 파일이 S3에 성공적으로 업로드되었습니다.", uploaded_file.name)
        return file_url

    except MissingConfigError:
        raise
    except ClientError as e:
        logger.error("S3 업로드 중 오류 발생: %s", e)
        return None
