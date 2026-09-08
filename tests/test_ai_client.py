import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from app.ai_client import AIClient, parse_json_response, ALL_PROVIDERS


def test_default_model_anthropic():
    client = AIClient("anthropic", api_key="test")
    assert "claude" in client.model or client.model == "claude-sonnet-4-20250514"


def test_default_model_ollama():
    client = AIClient("ollama")
    assert client.model == "llama3"


def test_default_base_url_ollama():
    client = AIClient("ollama")
    assert client.base_url == "http://localhost:11434"


def test_default_model_openai():
    client = AIClient("openai", api_key="test")
    assert client.model == "gpt-4o"
    assert client.base_url == "https://api.openai.com/v1"


def test_default_model_google():
    client = AIClient("google", api_key="test")
    assert client.model == "gemini-2.0-flash"


def test_default_model_openrouter():
    client = AIClient("openrouter", api_key="test")
    assert client.model == "anthropic/claude-sonnet-4"
    assert "openrouter.ai" in client.base_url


# --- Bedrock provider tests ---

def test_bedrock_in_all_providers():
    assert "bedrock" in ALL_PROVIDERS


def test_default_model_bedrock():
    client = AIClient("bedrock")
    assert client.model == "us.anthropic.claude-sonnet-4-6"


def test_bedrock_default_region():
    client = AIClient("bedrock")
    assert client.region == ""


def test_bedrock_custom_region():
    client = AIClient("bedrock", region="eu-west-1")
    assert client.region == "eu-west-1"


def test_bedrock_custom_model():
    client = AIClient("bedrock", model="us.anthropic.claude-opus-4-6-v1")
    assert client.model == "us.anthropic.claude-opus-4-6-v1"


def test_bedrock_client_with_explicit_credentials():
    client = AIClient("bedrock", api_key="AKIAIOSFODNN7EXAMPLE",
                      base_url="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                      region="us-west-2")
    bedrock = client._bedrock_client()
    assert bedrock.aws_region == "us-west-2"


def test_bedrock_client_without_credentials():
    client = AIClient("bedrock", region="us-east-1")
    bedrock = client._bedrock_client()
    assert bedrock.aws_region == "us-east-1"


def test_bedrock_client_default_region_fallback():
    client = AIClient("bedrock")
    bedrock = client._bedrock_client()
    assert bedrock.aws_region == "us-east-1"


@pytest.mark.asyncio
async def test_bedrock_chat_routes_correctly():
    client = AIClient("bedrock", api_key="AKIAEXAMPLE",
                      base_url="secret", region="us-east-1")
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="OK")]
    with patch.object(client, "_bedrock_client") as mock_bc:
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_message)
        mock_bc.return_value = mock_client
        result = await client._bedrock_chat("test prompt", 10)
        assert result == "OK"
        mock_client.messages.create.assert_called_once_with(
            model="us.anthropic.claude-sonnet-4-6",
            max_tokens=10,
            messages=[{"role": "user", "content": "test prompt"}],
        )


def test_bedrock_not_in_openai_compat():
    from app.ai_client import OPENAI_COMPAT_PROVIDERS
    assert "bedrock" not in OPENAI_COMPAT_PROVIDERS


def test_parse_json_response_plain():
    result = parse_json_response('{"score": 88}')
    assert result["score"] == 88


def test_parse_json_response_markdown():
    result = parse_json_response('```json\n{"score": 88}\n```')
    assert result["score"] == 88


def test_parse_json_response_markdown_no_lang():
    result = parse_json_response('```\n{"score": 88}\n```')
    assert result["score"] == 88


def test_parse_json_response_bad_json():
    with pytest.raises(Exception):
        parse_json_response("not json")


async def test_qwen_scoring_budget_is_for_final_answer(httpx_mock):
    httpx_mock.add_response(json={"message": {"content": '{"score": 80}', "thinking": "private reasoning"},
                                  "done_reason": "stop"})
    client = AIClient("ollama", model="qwen3.5:9b", base_url="http://127.0.0.1:11434")
    result = await client._ollama_chat("Return JSON", 1024)
    assert result == '{"score": 80}'
    assert json.loads(httpx_mock.get_request().content)["think"] is False


@pytest.mark.parametrize("response, message", [
    ({"message": {"content": "", "thinking": "Only reasoning"}}, "no final answer"),
    ({"message": {"content": '{"score": 80}'}, "done_reason": "length"}, "token limit"),
])
async def test_ollama_rejects_incomplete_answers(httpx_mock, response, message):
    httpx_mock.add_response(json=response)
    client = AIClient("ollama", base_url="http://127.0.0.1:11434")
    with pytest.raises(RuntimeError, match=message):
        await client._ollama_chat("Return JSON", 1024)


async def test_scoring_json_has_room_for_resume_job_and_answer(httpx_mock):
    httpx_mock.add_response(json={"message": {"content": '{"score": 80}'}, "done_reason": "stop"})
    client = AIClient("ollama", base_url="http://127.0.0.1:11434")
    await client.chat("Resume and job " * 1800, max_tokens=4096, json_mode=True)
    payload = json.loads(httpx_mock.get_request().content)
    assert payload["format"] == "json"
    assert payload["options"]["temperature"] == 0
    assert payload["options"]["num_ctx"] >= 16384
    assert payload["options"]["num_ctx"] > len(payload["messages"][0]["content"]) // 2 + 4096
