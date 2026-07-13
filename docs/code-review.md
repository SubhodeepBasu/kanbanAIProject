# Code Review Report

**Date:** 2026-07-13
**Scope:** Entire repository (no pending diff at time of review — the working tree was clean, so the full codebase was reviewed as-is rather than a changeset).
**Method:** 8 independent review angles (correctness line-scan, invariant/validation audit, cross-file contract tracing, reuse/duplication, simplification, efficiency, altitude, conventions-vs-`CLAUDE.md`/`AGENTS.md`), each verified against the actual source before inclusion. Findings below are all confirmed by direct code reading, with exact file/line references.

## Executive summary

The MVP is functionally complete and its test suite passes (33 tests: 22 backend, 11 frontend unit, 4 e2e — see `docs/PLAN.md`). This review found no issues in the tested happy paths, but surfaced **4 high-severity issues** around concurrent writes, an initial-load race, and a validation gap that can crash requests or the UI; several **medium-severity** reliability/efficiency gaps; and a set of **low-severity** duplication/cleanup/documentation items. Given the project's explicit "keep it simple, MVP-only, local single-user" scope (`AGENTS.md`), not everything here needs fixing before shipping further — priorities are called out at the end.

## Severity summary

| # | Severity | Area | Summary |
|---|---|---|---|
| F1 | High | Concurrency | AI board-mutation endpoint reads, waits up to 45s on OpenRouter, then overwrites the board with no version check — concurrent manual edits are silently lost |
| F2 | High | Reliability | Frontend pins the AI model to the exact value of the backend's own fallback model, permanently disabling the fallback retry it relies on |
| F3 | High | Data integrity | Initial board load race — interacting with the board before/without a successful fetch persists demo data over the user's real saved board |
| F4 | High | Validation / crash | Shallow board-shape validation lets malformed data get persisted, which later causes an uncaught 500 in the AI endpoint and can crash the board UI with no error boundary |
| F5 | Medium | Resource leak | SQLite connections are never closed (already logged as open debt, still unresolved) |
| F6 | Medium | Efficiency | Every board save does an extra, redundant read-back round trip |
| F7 | Medium | Efficiency / correctness | Column rename fires a full-board save on every keystroke, unsequenced |
| F8 | Medium | Error handling | Backend's real error messages (`detail`) are discarded by the frontend API client |
| F9 | Medium | Security / scope | Unauthenticated callers can override the AI model per-request against the shared API key |
| F10 | Medium | Consistency | `delete_card` and `move_card` disagree on how to handle a card orphaned from all columns |
| F11 | Low | Duplication | OpenRouter request + 429-retry logic duplicated between two functions in `ai.py` |
| F12 | Low | Duplication | Board-shape validation duplicated between `main.py` and `ai_actions.py` |
| F13 | Low | Duplication | UI markup/styling duplicated and already drifted (card vs. card preview; button/input styles) |
| F14 | Low | Documentation drift | Root `AGENTS.md`'s model decision no longer matches the code, and the mismatch means a non-free model is used for every AI action |
| F15 | Low | Cleanup | Pointless `useMemo` with no actual computation |
| F16 | Low | Scalability | Linear column/card scans re-run per operation instead of an index built once per batch |

---

## High severity

### F1 — Concurrent writes race between AI mutation and manual edits (data loss)

**Files:** `backend/main.py:94-131` (`ai_board_actions`), `frontend/src/components/KanbanBoard.tsx:149-175` (`handleSendAiPrompt`)

`ai_board_actions` reads the board once at the start (`main.py:94`), then makes an OpenRouter call that can take **up to 45 seconds** (`ai.py`'s `timeout=45.0`), then applies operations to that original snapshot and unconditionally overwrites the DB (`save_user_board`, `main.py:124`) — there is no version/timestamp check anywhere in `db.py`'s `save_user_board` (`db.py:144-159`, a plain `UPDATE ... WHERE user_id = ?`).

**Failure scenario:** User submits an AI prompt. While waiting on the slow OpenRouter round trip, they drag a card — that `PUT /api/board` completes quickly and commits to SQLite. When the AI response finally arrives, the backend overwrites SQLite with `(original snapshot + AI operations)`, silently reverting the drag in the database. On the frontend, `handleSendAiPrompt` also does `setBoard(result.board)` unconditionally (`KanbanBoard.tsx:161`), discarding any local UI state changed during the wait, independent of the backend issue.

**Recommendation:** At minimum, add an optimistic concurrency check (compare `updated_at`/a version column before the AI write and reject/retry on mismatch). This is a real risk any time an AI prompt takes several seconds, which is the common case.

### F2 — Frontend's hardcoded AI model equals the backend's fallback, so the fallback never fires

**Files:** `frontend/src/lib/api.ts:22`, `backend/ai.py:7-8`, `backend/ai.py:156-165`

```
// api.ts:22
const AI_BOARD_PATH = "/api/ai/board?username=user&model=openai/gpt-4o-mini";
```
```python
# ai.py:7-8
MODEL_NAME = "qwen/qwen3-coder:free"
FALLBACK_MODEL_NAME = "openai/gpt-4o-mini"
```
`run_board_action_prompt`'s retry guard is `status_code == 429 and model != FALLBACK_MODEL_NAME` (`ai.py:160`). Because the frontend always sends `model=openai/gpt-4o-mini` — which **is** `FALLBACK_MODEL_NAME` — this condition is always false for the real user-facing chat flow.

**Failure scenario:** OpenRouter rate-limits `gpt-4o-mini` (429). The AI sidebar's request fails outright with no retry, even though the code visibly has a fallback-retry mechanism — it just never applies to the path actual users go through, because the frontend already pre-selected the "fallback" model as its primary choice.

**Recommendation:** Either have the frontend stop pinning a model at all (let the backend's `MODEL_NAME`/`FALLBACK_MODEL_NAME` policy own this end-to-end), or give the backend a real primary→secondary chain that doesn't collapse to a no-op when the client's preferred model matches the fallback.

### F3 — Initial board-load race can overwrite the persisted board with demo data

**File:** `frontend/src/components/KanbanBoard.tsx:33-77`

`board` state is initialized to the hardcoded `initialData` demo board (`kanban.ts:39`, line 33 of `KanbanBoard.tsx`). A `useEffect` then fetches the real board and calls `setBoard(nextBoard)` on success (lines 41-67). Nothing disables interaction while `isLoading` is true, and nothing prevents `applyBoardChange` (lines 69-77) from firing against whatever `board` currently holds — including still-`initialData` if the fetch hasn't resolved yet, or never resolves (network error just sets an error banner and continues showing `initialData`).

**Failure scenario:** A returning user has previously customized their board. On a slow connection (or cold container start), they click "Add a card" before the `GET /api/board` response arrives. `applyBoardChange` computes the next state from `initialData` and fires `saveBoard(nextBoardState)` — a `PUT` that **permanently overwrites** their real saved board in SQLite with `demo board + one new card`. If the original `GET` then resolves afterward, `setBoard(nextBoard)` (the pre-edit fetched data) can also clobber the just-made local edit in the UI, compounding the confusion.

**Recommendation:** Disable board interaction (or queue/block mutations) until the initial fetch completes or definitively fails, and don't apply local edits on top of the demo seed data.

### F4 — Shallow board-shape validation cascades into an unhandled crash

**Files:** `backend/main.py:23-26` (`is_valid_board_shape`), `backend/main.py:117-121`, `backend/ai_actions.py:117-136` (`_apply_edit_card`), `frontend/src/components/KanbanBoard.tsx:247`, `frontend/src/components/KanbanColumn.tsx:59-65`

`is_valid_board_shape` only checks `isinstance(columns, list) and isinstance(cards, dict)` — it never checks that each column has a valid `cardIds: list[str]`, that each card value is itself a dict with the expected keys, or that every `cardIds` entry actually exists in `cards`. This is the **only** gate on `PUT /api/board` (`main.py:150`).

Meanwhile, the AI-operations block only catches `ValueError`:
```python
# main.py:117-121
try:
    assistant_message, operations = validate_ai_actions_payload(ai_result["payload"])
    next_board, applied_operations = apply_board_operations(board_data["board"], operations)
except ValueError as error:
    raise HTTPException(status_code=422, detail=f"Invalid AI operations: {error}") from error
```
But `_apply_edit_card` does unguarded item assignment once a card ID is found present: `cards[card_id]["title"] = title.strip()` (`ai_actions.py:132`) — if `cards[card_id]` isn't actually a dict (allowed to slip through by the shallow shape check), this raises `TypeError`, not `ValueError`.

**Failure scenario:** A `PUT /api/board` with `{"board": {"columns": [], "cards": {"card-1": "oops"}}}` passes validation and is persisted (there are no columns referencing it yet, so it's inert — until an AI prompt targets it). A later AI-generated `edit_card` operation for `card-1` hits `cards["card-1"]["title"] = ...`, a `str` doesn't support item assignment → unhandled `TypeError` → **500** instead of the intended `422`. Separately, if a `cardIds` entry ever references a card missing from `cards` (same shallow-validation gap), the frontend crashes outright: `column.cardIds.map((cardId) => board.cards[cardId])` (`KanbanBoard.tsx:247`) produces `undefined`, and `KanbanColumn` maps over it doing `card.id` on `undefined` (`KanbanColumn.tsx:60-64`) with **no error boundary anywhere in the app** — the whole board goes blank.

**Recommendation:** Deepen `is_valid_board_shape` to validate columns/cards element-wise and cross-reference `cardIds` against `cards` keys; widen the AI-operations except clause (or catch a common base exception) so malformed data degrades to a clean `422`/`502` instead of a raw 500; consider a minimal React error boundary around the board render.

---

## Medium severity

### F5 — SQLite connections are opened per call and never closed *(already tracked, still open)*

**File:** `backend/db.py:61-67`

```python
def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    connection.execute("PRAGMA journal_mode = WAL;")
    return connection
```
Every caller uses `with connection:` — but per Python's `sqlite3` docs, that context manager only governs the transaction (commit/rollback on exit); it does **not** close the connection. Every `GET`/`PUT /api/board` and `POST /api/ai/board` call leaks one (or two — see F6) OS-level connections/file handles.

This is already logged in `PROJECT_DESIGN_DOCUMENT.md`'s incident register (ID 11, "ResourceWarning for unclosed sqlite connections in tests... Status: Open"), so it's known debt rather than a new finding — but it remains unresolved in the current code and is worth closing out rather than leaving indefinitely, since under sustained traffic it can exhaust the process's file-descriptor limit.

**Recommendation:** Wrap connection usage in `with _connect(db_path) as connection:` plus an explicit `connection.close()` (e.g. via `try/finally` or a `contextlib.closing` wrapper), or switch to a small connection-per-request pattern with guaranteed cleanup.

### F6 — Every board save does a redundant read-back round trip

**File:** `backend/db.py:144-159`

```python
def save_user_board(db_path: Path, username: str, board: dict[str, Any]) -> dict[str, Any] | None:
    with _connect(db_path) as connection:
        ...
        connection.execute("UPDATE boards SET board_json = ?, updated_at = ... WHERE user_id = ?", ...)
    return get_user_board(db_path, username)
```
After writing, it opens a **second** connection and re-queries the row it just wrote, purely to hand back `board`/`updatedAt` to the caller — instead of computing `updated_at` once (e.g. via SQLite's `RETURNING`, or simply returning the `board` the caller already passed in plus a computed timestamp).

**Cost:** every `PUT /api/board` and every AI mutation pays for 2 full SQLite connection opens (each with its own `PRAGMA` setup) instead of 1. Combined with F5, this doubles the leaked-connection rate too.

### F7 — Per-keystroke full-board save on column rename, unsequenced

**Files:** `frontend/src/components/KanbanColumn.tsx:49-52`, `frontend/src/components/KanbanBoard.tsx:69-77, 105-112`

```tsx
// KanbanColumn.tsx:49-52
<input
  value={column.title}
  onChange={(event) => onRename(column.id, event.target.value)}
  ...
```
Every keystroke calls `onRename` → `handleRenameColumn` → `applyBoardChange`, which fires a fire-and-forget `saveBoard(...)` (a full-board `PUT`) with no debounce, and no request sequencing/abort logic anywhere in `api.ts` or `KanbanBoard.tsx`.

**Cost / failure scenario:** Typing a 20-character title fires 20 full-board `PUT` requests. If network jitter causes an earlier keystroke's request to be processed by the server *after* a later one, SQLite ends up holding a stale, incomplete title — the next reload can show an earlier partial value than what the user saw on-screen before refreshing. This same fire-and-forget, unsequenced pattern applies to every mutation path (drag, add, delete), not just rename.

**Recommendation:** Debounce text-input-driven saves, and/or track a monotonically increasing save sequence number so an out-of-order response can be discarded client-side.

### F8 — Backend error detail is discarded by the frontend API client

**File:** `frontend/src/lib/api.ts:24-56`

`fetchBoard`, `saveBoard`, and `requestAiBoardAction` all follow the same pattern: check `response.ok`, and if not, `throw new Error("<fixed generic string>")` — none of them read the response body. But FastAPI's `HTTPException` responses carry a specific, useful `detail` field throughout `main.py` (missing API key → 503, invalid AI operation → 422 with the exact validation message, unknown user → 404, etc.).

**Failure scenario:** `OPENROUTER_API_KEY` isn't configured, or the AI hallucinates a `move_card` targeting a nonexistent card. The backend correctly reports the precise cause, but the AI sidebar only ever shows "AI request failed. Your board has not been changed." — there's no way for a user or an operator debugging a stuck deployment to tell a missing API key apart from an AI hallucination or a rate limit.

**Recommendation:** Parse the JSON body on error responses and surface `detail` (falling back to the generic message only if parsing fails).

### F9 — Unauthenticated per-request AI model override

**Files:** `backend/main.py:42` (`ai_connectivity_test(live: bool = False, model: str = MODEL_NAME)`), `backend/main.py:87` (`ai_board_actions(payload, username: str = "user", model: str = MODEL_NAME)`)

Both AI endpoints accept an arbitrary `model` query parameter with no authentication on the API itself (the login gate is purely client-side — see `AuthGate.tsx`, an explicitly accepted MVP limitation per `docs/PLAN.md` Part 4). Nothing about the written requirements calls for a caller-selectable model.

**Failure scenario:** Since the container exposes port 8000 directly (`docker-compose.yml`), any client on the same network can call `POST /api/ai/board?model=<any-openrouter-model>` and bill the shared `OPENROUTER_API_KEY` for an arbitrary (potentially expensive, non-free) model, bypassing the intended default/fallback policy entirely.

**Recommendation:** Given the "no extra features" simplicity mandate in `AGENTS.md`, consider dropping the caller-overridable `model` parameter from these routes (or gating it behind the same auth boundary once real auth exists).

### F10 — `delete_card` and `move_card` disagree on how to handle a card orphaned from all columns

**File:** `backend/ai_actions.py:59-67` (`_find_column_containing_card`), `139-167` (`_apply_move_card`), `170-186` (`_apply_delete_card`)

`_apply_move_card` calls `_find_column_containing_card`, which **raises** `ValueError("Card not found in any column: ...")` if the card isn't referenced by any column's `cardIds`. `_apply_delete_card` doesn't reuse that helper — it inlines its own scan (lines 181-184) and is silently tolerant: if the card isn't found in any column, it just proceeds to `del cards[card_id]` with no error.

**Failure scenario:** If board data ever reaches an inconsistent state where a card exists in `cards` but isn't referenced by any column (reachable via the same shallow-validation gap as F4), `move_card` on that card hard-fails with a `422`, while `delete_card` on the exact same card silently "succeeds" — the two operations disagree about what counts as valid input for the same underlying invariant.

**Recommendation:** Have `_apply_delete_card` reuse `_find_column_containing_card` (or a shared variant that returns `None` instead of raising) so both operations treat "orphaned card" the same way.

---

## Low severity

### F11 — Duplicated OpenRouter request-building + 429-retry logic

**File:** `backend/ai.py`

`run_connectivity_test` (lines 63-88) uses the shared `call_openrouter_prompt` helper and then hand-rolls a "catch 429, swap in `FALLBACK_MODEL_NAME`, retry once" block (lines 70-78). `run_board_action_prompt` (lines 91-180) does **not** reuse `call_openrouter_prompt` — it defines its own nested `make_request` (lines 133-151) that reconstructs the same request, then re-implements the identical retry-on-429 pattern a second time (lines 156-165). If OpenRouter's retry policy ever needs to change (different status codes, backoff, a different fallback model), it's easy to update one copy and forget the other.

**Recommendation:** Extract one `call_with_fallback(make_request_fn, model)` wrapper (or generalize `call_openrouter_prompt` to accept an arbitrary message list) and have both functions use it.

### F12 — Duplicated board-shape validation

**Files:** `backend/main.py:23-26`, `backend/ai_actions.py:25-26`

```python
# main.py:23-26
def is_valid_board_shape(board: dict[str, Any]) -> bool:
    columns = board.get("columns")
    cards = board.get("cards")
    return isinstance(columns, list) and isinstance(cards, dict)
```
```python
# ai_actions.py:25-26 (inside apply_board_operations)
if not isinstance(columns, list) or not isinstance(cards, dict):
    raise ValueError("Board shape is invalid")
```
Same rule, two independently-maintained copies with two different failure protocols (bool-returning vs. exception-raising). If this check is ever deepened (see F4's recommendation), whoever fixes one call site has no signal that the other needs the same fix.

**Recommendation:** Move the check into one function that both call sites use (adapt the caller to the bool-vs-exception difference at the call site, not inside the shared check).

### F13 — Duplicated and drifted UI markup/styling

**Files:** `frontend/src/components/KanbanCard.tsx:24-40` vs. `KanbanCardPreview.tsx:8-17`; button styling in `NewCardForm.tsx:48`, `AuthGate.tsx:96-97`, `AiSidebar.tsx:95`; input styling in `NewCardForm.tsx:33,43` vs. `AuthGate.tsx:66,80`

`KanbanCardPreview` exists solely to render the drag-overlay ghost of a `KanbanCard` but duplicates its container/title/details markup verbatim instead of sharing a presentational component — any visual change to a real card (padding, a new badge, truncation) has to be manually re-applied to the preview or it visibly diverges. This has already happened with the "purple pill CTA" pattern: `NewCardForm.tsx:48` and `AuthGate.tsx:96-97` use `hover:brightness-110`, while `AiSidebar.tsx:95` uses `hover:brightness-105` with a different corner radius (`rounded-2xl` vs. `rounded-full`) — no apparent design reason, just drift from copy-pasting.

**Recommendation:** Extract a shared `CardShell`, `PrimaryButton`, and `TextField` component so these styles have one source of truth.

### F14 — Documentation drift: the model spec in `AGENTS.md` no longer matches the code

**Files:** `AGENTS.md:27` (root), `backend/ai.py:7-8`, `frontend/src/lib/api.ts:22`

Root `AGENTS.md`'s Technical Decisions section states: *"Use `openai/gpt-oss-120b:free` as the model."* That model appears nowhere in the actual code — `backend/ai.py` defaults to `qwen/qwen3-coder:free` with fallback `openai/gpt-4o-mini`, and the frontend pins `openai/gpt-4o-mini` directly (see F2). `PROJECT_DESIGN_DOCUMENT.md` does acknowledge this drift in its "Model Configuration Note," but the root `AGENTS.md` — the document `CLAUDE.md` itself points to as the source of business requirements — was never updated to match.

**Cost:** the original decision specified a `:free` model; the code now bills the shared API key against `gpt-4o-mini` (not free) for every single AI sidebar action, a quiet cost regression from the written spec. A future contributor reading `AGENTS.md` as ground truth would implement against a model that was silently abandoned.

**Recommendation:** Update root `AGENTS.md`'s Technical Decisions section to reflect the actual current model policy, or restore the original model if the drift was unintentional.

### F15 — Pointless `useMemo`

**File:** `frontend/src/components/KanbanBoard.tsx:85`

```tsx
const cardsById = useMemo(() => board.cards, [board.cards]);
```
This memoizes a plain property read with no computation — `board.cards` is already the exact value being "memoized." It adds indirection and a dependency array to maintain for zero benefit.

### F16 — Linear scans re-run per operation instead of an index built once per batch

**Files:** `backend/ai_actions.py:52-67` (`_find_column`, `_find_column_containing_card`), used repeatedly inside `apply_board_operations`'s per-operation dispatch (lines 28-47); also `ai_actions.py:21`'s unconditional `copy.deepcopy(board)` even when `operations` is empty.

Each operation in an AI-generated batch re-scans the full `columns` list (and each column's `cardIds`) rather than building a `card_id -> column` index once per `apply_board_operations` call; the board is also deep-copied before checking whether there's anything to apply at all. Not a real cost today given the MVP's board sizes (5 columns, single-digit cards), but worth a note if boards or AI operation batches grow.

---

## Cross-references / things intentionally **not** flagged

- **Client-side-only authentication** (`AuthGate.tsx`) — this is an explicit, documented MVP decision (`docs/PLAN.md` Part 4, `AGENTS.md`'s Limitations section), not a gap.
- **Full-document board overwrite with no patch protocol** — already called out as accepted technical debt in `PROJECT_DESIGN_DOCUMENT.md`'s "Known Limitations" section; F1 above is a specific, concrete consequence of this accepted design worth prioritizing regardless.
- **AI operation batch atomicity** — verified correct: `apply_board_operations` mutates only a deep copy, and if any operation raises, the exception propagates before `main.py` ever calls `save_user_board`, so a partially-applied batch is never persisted.
- Query-string encoding of `model=openai/gpt-4o-mini` (the `/` character) — verified **not** a bug; `/` is a valid unreserved character in an HTTP query component and FastAPI/Starlette parses it correctly.

## Recommended priority order

1. **F4** (validation/crash) and **F1** (concurrency/data loss) — both are real bugs reachable through normal use, not just edge cases.
2. **F2** (dead fallback) and **F3** (initial-load race) — quick, high-value fixes; F2 in particular is a one-line-cause reliability gap.
3. **F5/F6** (connection leak + redundant round trip) — cheap to fix together while already touching `db.py`, and F5 closes out an already-logged open incident.
4. **F8** (surface real errors) and **F9** (drop the unauthenticated model override) — small, low-risk changes with good payoff for debuggability and cost control.
5. **F7, F10, F11-F16** — worth doing opportunistically or in a cleanup pass; none are urgent given the MVP's current scope and traffic profile.
