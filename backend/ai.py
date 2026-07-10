import json
from typing import Any

import httpx

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL_NAME = "qwen/qwen3-coder:free"
FALLBACK_MODEL_NAME = "openai/gpt-4o-mini"


def build_openrouter_payload(prompt: str, model: str = MODEL_NAME) -> dict[str, Any]:
    return {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
    }


def extract_assistant_text(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("Missing choices in OpenRouter response")

    message = choices[0].get("message", {})
    content = message.get("content")

    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        text = "".join(parts).strip()
        if text:
            return text

    raise ValueError("Could not parse assistant content")


def call_openrouter_prompt(
    api_key: str,
    prompt: str,
    model: str = MODEL_NAME,
    timeout: float = 30.0,
) -> str:
    response = httpx.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=build_openrouter_payload(prompt, model=model),
        timeout=timeout,
    )
    response.raise_for_status()
    return extract_assistant_text(response.json())


def run_connectivity_test(api_key: str, model: str = MODEL_NAME) -> dict[str, Any]:
    prompt = "What is 2+2? Reply with only the final numeric answer."
    used_fallback = False
    used_model = model

    try:
        answer = call_openrouter_prompt(api_key, prompt, model=model)
    except httpx.HTTPStatusError as error:
        status_code = error.response.status_code
        should_retry = status_code == 429 and model != FALLBACK_MODEL_NAME
        if not should_retry:
            raise

        used_fallback = True
        used_model = FALLBACK_MODEL_NAME
        answer = call_openrouter_prompt(api_key, prompt, model=FALLBACK_MODEL_NAME)

    contains_four = "4" in answer
    return {
        "model": used_model,
        "requestedModel": model,
        "fallbackUsed": used_fallback,
        "prompt": prompt,
        "answer": answer,
        "containsFour": contains_four,
    }


def run_board_action_prompt(
    api_key: str,
    user_prompt: str,
    board: dict[str, Any],
    model: str = MODEL_NAME,
    timeout: float = 45.0,
) -> dict[str, Any]:
    system_message = (
        "You are a project management assistant for a kanban board. "
        "Return strict JSON only with keys assistantMessage and operations. "
        "operations must be an array of objects using only these operation types: "
        "create_card, edit_card, move_card, delete_card, rename_column. "
        "For each operation, include required IDs exactly as fields: "
        "rename_column requires columnId and title; "
        "create_card requires columnId, cardId, title, details; "
        "edit_card requires cardId and at least one of title/details; "
        "move_card requires cardId and toColumnId (optional index); "
        "delete_card requires cardId. "
        "Never use column names in place of columnId. "
        "Do not include markdown fences."
    )

    user_content = {
        "instruction": user_prompt,
        "board": board,
        "outputSchema": {
            "assistantMessage": "string",
            "operations": [
                {
                    "type": "create_card|edit_card|move_card|delete_card|rename_column",
                    "requiredFieldsByType": {
                        "rename_column": ["type", "columnId", "title"],
                        "create_card": ["type", "columnId", "cardId", "title", "details"],
                        "edit_card": ["type", "cardId", "title|details"],
                        "move_card": ["type", "cardId", "toColumnId"],
                        "delete_card": ["type", "cardId"],
                    },
                }
            ],
        },
    }

    def make_request(selected_model: str) -> str:
        response = httpx.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": selected_model,
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": json.dumps(user_content)},
                ],
                "temperature": 0,
            },
            timeout=timeout,
        )
        response.raise_for_status()
        return extract_assistant_text(response.json())

    used_model = model
    used_fallback = False

    try:
        raw_text = make_request(model)
    except httpx.HTTPStatusError as error:
        status_code = error.response.status_code
        should_retry = status_code == 429 and model != FALLBACK_MODEL_NAME
        if not should_retry:
            raise
        used_model = FALLBACK_MODEL_NAME
        used_fallback = True
        raw_text = make_request(FALLBACK_MODEL_NAME)

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as error:
        raise ValueError("AI response was not valid JSON") from error

    if not isinstance(parsed, dict):
        raise ValueError("AI response root must be a JSON object")

    return {
        "model": used_model,
        "requestedModel": model,
        "fallbackUsed": used_fallback,
        "payload": parsed,
    }
