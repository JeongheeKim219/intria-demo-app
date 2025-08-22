import streamlit as st
import boto3
from botocore.exceptions import ClientError
import uuid
import os

def get_s3_client():
    """
    Streamlit secrets를 사용하여 boto3 S3 클라이언트를 생성하고 반환합니다.
    """
    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=st.secrets["aws"]["aws_access_key_id"],
            aws_secret_access_key=st.secrets["aws"]["aws_secret_access_key"],
            region_name=st.secrets["aws"]["region_name"]
        )
        return s3_client
    except Exception as e:
        st.error(f"S3 클라이언트 생성 중 오류 발생: {e}")
        return None

def upload_file_to_s3(uploaded_file):
    """
    st.file_uploader로 업로드된 파일 객체를 S3에 직접 업로드합니다.
    성공 시 S3 객체 URL을, 실패 시 None을 반환합니다.
    """
    s3_client = get_s3_client()
    if s3_client is None or uploaded_file is None:
        return None

    # Django 코드의 uuid 로직을 그대로 재사용하여 고유한 파일명 생성
    bucket_name = st.secrets["aws"]["s3_bucket_name"]
    file_name, file_extension = os.path.splitext(uploaded_file.name)
    object_name = f"uploads/{file_name}_{uuid.uuid4()}{file_extension}"

    try:
        # Pre-signed URL 방식 대신, 서버에서 직접 파일 객체를 업로드합니다.
        # 이 방식이 Streamlit에서는 훨씬 간단하고 효율적입니다.
        s3_client.upload_fileobj(
            uploaded_file,
            bucket_name,
            object_name,
            ExtraArgs={'ContentType': uploaded_file.type}
        )
        
        # 업로드된 파일의 URL 생성 (옵션)
        # ACL 설정에 따라 접근이 안될 수도 있습니다.
        file_url = f"https://{bucket_name}.s3.{st.secrets['aws']['region_name']}.amazonaws.com/{object_name}"
        
        st.success(f"'{uploaded_file.name}' 파일이 S3에 성공적으로 업로드되었습니다.")
        return file_url

    except ClientError as e:
        st.error(f"S3 업로드 중 오류 발생: {e}")
        return None