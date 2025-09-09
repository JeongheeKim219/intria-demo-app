import io
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src.aws_utils import upload_file_to_s3


def test_upload_file_to_s3_success():
    mock_file = io.BytesIO(b'data')
    mock_file.name = 'test.png'
    mock_file.type = 'image/png'

    mock_client = MagicMock()
    mock_st = SimpleNamespace(
        secrets={'aws': {
            'aws_access_key_id': 'id',
            'aws_secret_access_key': 'secret',
            'aws_region_name': 'us-east-1',
            'aws_storage_bucket_name': 'bucket'
        }},
        success=lambda msg: None,
        error=lambda msg: None
    )

    with patch('src.aws_utils.st', mock_st), \
         patch('src.aws_utils.get_s3_client', return_value=mock_client), \
         patch('src.aws_utils.uuid.uuid4', return_value='1234'):
        url = upload_file_to_s3(mock_file)

    mock_client.upload_fileobj.assert_called_once_with(
        mock_file,
        'bucket',
        'uploads/1234.png',
        ExtraArgs={'ContentType': 'image/png'}
    )
    assert url == 'https://bucket.s3.us-east-1.amazonaws.com/uploads/1234.png'
