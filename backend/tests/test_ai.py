import httpx

from ai import (
    FALLBACK_MODEL_NAME,
    MODEL_NAME,
    build_openrouter_payload,
    extract_assistant_text,
    run_connectivity_test,
)


def test_build_openrouter_payload_uses_expected_model() -> None:
    payload = build_openrouter_payload("2+2")

    assert payload["model"] == MODEL_NAME
    assert payload["messages"][0]["content"] == "2+2"
    assert payload["temperature"] == 0


def test_extract_assistant_text_supports_string_content() -> None:
    text = extract_assistant_text(
        {
            "choices": [
                {
                    "message": {
                        "content": "4",
                    }
                }
            ]
        }
    )

    assert text == "4"


def test_extract_assistant_text_supports_list_content() -> None:
    text = extract_assistant_text(
        {
            "choices": [
                {
                    "message": {
                        "content": [
                            {"type": "text", "text": "The answer is "},
                            {"type": "text", "text": "4"},
                        ]
                    }
                }
            ]
        }
    )

    assert text == "The answer is 4"


def test_run_connectivity_test_retries_once_on_429(monkeypatch) -> None:
    calls: list[str] = []

    def fake_call(api_key: str, prompt: str, model: str = MODEL_NAME, timeout: float = 30.0) -> str:
        del api_key, prompt, timeout
        calls.append(model)
        if len(calls) == 1:
            request = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
            response = httpx.Response(429, request=request)
            raise httpx.HTTPStatusError("429", request=request, response=response)
        return "4"

    monkeypatch.setattr("ai.call_openrouter_prompt", fake_call)

    result = run_connectivity_test("demo-key")

    assert calls == [MODEL_NAME, FALLBACK_MODEL_NAME]
    assert result["requestedModel"] == MODEL_NAME
    assert result["model"] == FALLBACK_MODEL_NAME
    assert result["fallbackUsed"] is True
    assert result["containsFour"] is True


def test_run_connectivity_test_retries_with_primary_model_when_called_with_fallback(
    monkeypatch,
) -> None:
    """A caller that already requests the fallback model still gets a real retry on 429."""
    calls: list[str] = []

    def fake_call(api_key: str, prompt: str, model: str = MODEL_NAME, timeout: float = 30.0) -> str:
        del api_key, prompt, timeout
        calls.append(model)
        if len(calls) == 1:
            request = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
            response = httpx.Response(429, request=request)
            raise httpx.HTTPStatusError("429", request=request, response=response)
        return "4"

    monkeypatch.setattr("ai.call_openrouter_prompt", fake_call)

    result = run_connectivity_test("demo-key", model=FALLBACK_MODEL_NAME)

    assert calls == [FALLBACK_MODEL_NAME, MODEL_NAME]
    assert result["requestedModel"] == FALLBACK_MODEL_NAME
    assert result["model"] == MODEL_NAME
    assert result["fallbackUsed"] is True


def test_run_connectivity_test_does_not_retry_non_429(monkeypatch) -> None:
    def fake_call(api_key: str, prompt: str, model: str = MODEL_NAME, timeout: float = 30.0) -> str:
        del api_key, prompt, model, timeout
        request = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
        response = httpx.Response(500, request=request)
        raise httpx.HTTPStatusError("500", request=request, response=response)

    monkeypatch.setattr("ai.call_openrouter_prompt", fake_call)

    try:
        run_connectivity_test("demo-key")
        assert False, "Expected HTTPStatusError"
    except httpx.HTTPStatusError as error:
        assert error.response.status_code == 500
