import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from ai import MODEL_NAME, run_board_action_prompt, run_connectivity_test
from ai_actions import apply_board_operations, validate_ai_actions_payload
from db import get_user_board, init_database, save_user_board


class BoardUpdateRequest(BaseModel):
    board: dict[str, Any]


class AiBoardRequest(BaseModel):
    prompt: str


def is_valid_board_shape(board: dict[str, Any]) -> bool:
    columns = board.get("columns")
    cards = board.get("cards")
    return isinstance(columns, list) and isinstance(cards, dict)


def create_app(
    frontend_dist_dir: str | None = None,
    db_path: str | None = None,
) -> FastAPI:
    app = FastAPI(title="Project Management MVP API", version="0.1.0")
    db_file = Path(db_path or os.getenv("DB_PATH") or "/data/pm.db")
    init_database(db_file)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "pm-backend"}

    @app.get("/api/ai/test")
    def ai_connectivity_test(live: bool = False, model: str = MODEL_NAME) -> dict[str, Any]:
        selected_model = model.strip() or MODEL_NAME

        if not live:
            return {
                "status": "ready",
                "model": selected_model,
                "message": "Set live=true to run the OpenRouter 2+2 connectivity check.",
            }

        api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        if not api_key:
            raise HTTPException(
                status_code=503,
                detail="OPENROUTER_API_KEY is not configured",
            )

        try:
            result = run_connectivity_test(api_key, model=selected_model)
        except Exception as error:
            raise HTTPException(
                status_code=502,
                detail=f"OpenRouter request failed: {error}",
            ) from error

        return {
            "status": "ok",
            **result,
        }

    @app.get("/api/board")
    def read_board(username: str = "user") -> dict[str, Any]:
        board_data = get_user_board(db_file, username)
        if board_data is None:
            raise HTTPException(status_code=404, detail="User or board not found")
        return {
            "username": username,
            "board": board_data["board"],
            "updatedAt": board_data["updatedAt"],
        }

    @app.post("/api/ai/board")
    def ai_board_actions(
        payload: AiBoardRequest,
        username: str = "user",
        model: str = MODEL_NAME,
    ) -> dict[str, Any]:
        prompt = payload.prompt.strip()
        if not prompt:
            raise HTTPException(status_code=422, detail="Prompt cannot be empty")

        selected_model = model.strip() or MODEL_NAME
        board_data = get_user_board(db_file, username)
        if board_data is None:
            raise HTTPException(status_code=404, detail="User or board not found")

        api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        if not api_key:
            raise HTTPException(
                status_code=503,
                detail="OPENROUTER_API_KEY is not configured",
            )

        try:
            ai_result = run_board_action_prompt(
                api_key=api_key,
                user_prompt=prompt,
                board=board_data["board"],
                model=selected_model,
            )
        except ValueError as error:
            raise HTTPException(status_code=502, detail=f"Invalid AI response: {error}") from error
        except Exception as error:
            raise HTTPException(status_code=502, detail=f"OpenRouter request failed: {error}") from error

        try:
            assistant_message, operations = validate_ai_actions_payload(ai_result["payload"])
            next_board, applied_operations = apply_board_operations(board_data["board"], operations)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=f"Invalid AI operations: {error}") from error

        if applied_operations:
            saved = save_user_board(db_file, username, next_board)
            if saved is None:
                raise HTTPException(status_code=404, detail="User or board not found")
            result_board = saved["board"]
            updated_at = saved["updatedAt"]
        else:
            result_board = board_data["board"]
            updated_at = board_data["updatedAt"]

        return {
            "status": "ok",
            "username": username,
            "assistantMessage": assistant_message,
            "operationsApplied": applied_operations,
            "board": result_board,
            "updatedAt": updated_at,
            "model": ai_result["model"],
            "requestedModel": ai_result["requestedModel"],
            "fallbackUsed": ai_result["fallbackUsed"],
        }

    @app.put("/api/board")
    def write_board(
        payload: BoardUpdateRequest,
        username: str = "user",
    ) -> dict[str, Any]:
        if not is_valid_board_shape(payload.board):
            raise HTTPException(status_code=422, detail="Invalid board payload")

        board_data = save_user_board(db_file, username, payload.board)
        if board_data is None:
            raise HTTPException(status_code=404, detail="User or board not found")

        return {
            "username": username,
            "board": board_data["board"],
            "updatedAt": board_data["updatedAt"],
        }

    @app.get("/hello", response_class=HTMLResponse)
    def hello() -> str:
        return """<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width,initial-scale=1\" />
    <title>PM MVP Hello</title>
    <style>
      body {
        margin: 0;
        font-family: system-ui, -apple-system, Segoe UI, sans-serif;
        background: #f7f8fb;
        color: #032147;
      }
      main {
        min-height: 100vh;
        display: grid;
        place-items: center;
        padding: 24px;
      }
      .card {
        max-width: 720px;
        width: 100%;
        background: #fff;
        border: 1px solid rgba(3, 33, 71, 0.1);
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 16px 30px rgba(3, 33, 71, 0.08);
      }
      h1 {
        margin: 0 0 8px;
      }
      p {
        margin: 0;
        color: #888888;
      }
      code {
        color: #209dd7;
      }
    </style>
  </head>
  <body>
    <main>
      <section class=\"card\">
        <h1>Hello from FastAPI in Docker</h1>
        <p>Try <code>/api/health</code> for the JSON API check.</p>
      </section>
    </main>
  </body>
</html>
"""

    default_dist = Path(__file__).resolve().parent.parent / "frontend" / "out"
    dist_dir = Path(
        frontend_dist_dir
        or os.getenv("FRONTEND_DIST_DIR")
        or default_dist
    )
    if dist_dir.exists():
        # Mount static site at root after API routes so /api stays accessible.
        app.mount("/", StaticFiles(directory=str(dist_dir), html=True), name="frontend")

    return app


app = create_app()
