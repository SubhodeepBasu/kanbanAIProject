# Part 5: SQLite Data Model (Board as JSON Blob)

## Goals

- Store one Kanban board per user as a single JSON document.
- Keep schema simple for MVP.
- Support future multi-user expansion.
- Persist data across container restarts.

## Database file location

- Recommended runtime path in container: `/data/pm.db`
- This aligns with the existing Docker named volume mounted at `/data`.
- Result: board data survives container restart/recreate.

## Proposed schema

```sql
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS boards (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL UNIQUE,
  board_json TEXT NOT NULL,
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
```

## Data contract for board_json

- `board_json` stores the full frontend board shape as JSON text:
  - `columns`: array
  - `cards`: object map by card id
- Backend validates payload structure before saving.
- API replaces the full board JSON blob per write in MVP.

## Initialization and migration strategy

At backend startup:

1. Ensure the DB directory exists (for example, create `/data` if needed).
2. Open SQLite connection to `/data/pm.db`.
3. Set pragmas:
   - `PRAGMA foreign_keys = ON;`
   - `PRAGMA journal_mode = WAL;`
4. Execute `CREATE TABLE IF NOT EXISTS` statements above.
5. Ensure baseline user row exists for `username = 'user'`.
6. Ensure that user has a board row; if missing, seed with initial board JSON.

Migration approach for MVP:

- Use an internal `schema_version` integer managed in code for now.
- Keep migrations manual and explicit in startup code until schema complexity increases.
- Introduce Alembic only when schema evolution becomes non-trivial.

## Read and write behavior (for Part 6)

- Read board:
  - Resolve user by username.
  - Return `board_json` payload.
- Write board:
  - Resolve user by username.
  - Validate incoming JSON shape.
  - Upsert full `board_json` for that user.
  - Update `updated_at`.

## Why this approach

Pros:

- Minimal schema and low implementation complexity.
- Exact match to frontend board model.
- Fast delivery for MVP.

Cons:

- Limited queryability inside board content (cards/columns not relational).
- Whole-document overwrite can increase write size.
- Concurrent edits are harder than normalized models.

Rationale:

- These trade-offs are acceptable for the MVP scope.
- The model can be normalized later if advanced querying or multi-editor concurrency is required.

## Test plan (Part 6 reference)

- Unit:
  - DB init creates tables and index when DB is missing.
  - Initial seed creates default `user` and board.
  - Read returns valid board JSON.
  - Write persists and updates `updated_at`.
- Integration:
  - Persistence verified across container restart.
  - Read after write returns latest board JSON.

## Open decision for approval

- Confirm this schema and strategy as the approved baseline for Part 6 implementation.
