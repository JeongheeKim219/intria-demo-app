import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src.ai_utils import analyze_text_with_gpt


def test_analyze_text_with_gpt_success():
    result_json = json.dumps({
        'data_analysis_results': {
            'content_type': '소셜 미디어',
            'main_topics': ['topic'],
            'entities': [],
            'keywords': []
        },
        'creative_profiling_results': {
            'inferred_user_interests': [],
            'new_tag_suggestions': [],
            'profiler_summary': 'summary'
        }
    })

    mock_response = SimpleNamespace(
        choices=[SimpleNamespace(
            message=SimpleNamespace(
                tool_calls=[SimpleNamespace(
                    function=SimpleNamespace(arguments=result_json)
                )]
            )
        )]
    )

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    mock_st = SimpleNamespace(
        secrets={'openai': {'api_key': 'key'}},
        success=lambda msg: None,
        error=lambda msg: None
    )

    with patch('src.ai_utils.OpenAI', return_value=mock_client), \
         patch('src.ai_utils.st', mock_st):
        result = analyze_text_with_gpt('hello')

    mock_client.chat.completions.create.assert_called_once()
    assert result['creative_profiling_results']['profiler_summary'] == 'summary'
