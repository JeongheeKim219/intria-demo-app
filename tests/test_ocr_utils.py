from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src.ocr_utils import extract_text_with_clova_ocr


def test_extract_text_with_clova_ocr_success():
    mock_response = MagicMock()
    mock_response.json.return_value = {
        'images': [{
            'fields': [
                {'inferText': 'Hello'},
                {'inferText': 'World'}
            ]
        }]
    }
    mock_response.raise_for_status.return_value = None

    mock_st = SimpleNamespace(
        secrets={'naver_ocr': {
            'api_url': 'http://api',
            'secret_key': 'secret'
        }},
        success=lambda msg: None,
        error=lambda msg: None
    )

    with patch('src.ocr_utils.st', mock_st), \
         patch('src.ocr_utils.requests.post', return_value=mock_response) as mock_post:
        text = extract_text_with_clova_ocr('http://image')

    mock_post.assert_called_once()
    assert text == 'Hello World'
