# Frontend Agent Notes

This document describes the current frontend implementation in `frontend/` so future work can integrate cleanly without re-discovery.

## Purpose

The frontend is a Next.js app that currently provides a polished, single-page Kanban demo with local in-memory state.

## Stack and tooling

- Framework: Next.js 16 (App Router) with React 19 and TypeScript.
- Styling: Tailwind CSS v4 plus CSS custom properties in `src/app/globals.css`.
- Drag and drop: `@dnd-kit/core` and `@dnd-kit/sortable`.
- Unit tests: Vitest + Testing Library + jsdom.
- E2E tests: Playwright.

## Runtime shape

- Route: `src/app/page.tsx` renders `KanbanBoard` as the home page.
- Root layout: `src/app/layout.tsx` sets metadata and Google fonts.
- Global design tokens: `src/app/globals.css` defines project color variables aligned with project requirements.

## Core components

- `src/components/KanbanBoard.tsx`
  - Owns board state in React local state (`BoardData`).
  - Handles card drag start/end and delegates movement logic to `moveCard`.
  - Handles column rename, card add, and card delete operations.
  - Renders five columns and a drag overlay preview.

- `src/components/KanbanColumn.tsx`
  - Droppable column container.
  - Editable column title input.
  - Sortable card list plus empty-state drop target.
  - Includes `NewCardForm` to add cards in-place.

- `src/components/KanbanCard.tsx`
  - Sortable draggable card with title/details.
  - Provides Remove action per card.

- `src/components/KanbanCardPreview.tsx`
  - Visual preview used by drag overlay.

- `src/components/NewCardForm.tsx`
  - Expand/collapse form for creating a card.
  - Validates non-empty title and trims inputs.

## Data model and behavior

- Source: `src/lib/kanban.ts`.
- Types:
  - `Card` = `{ id, title, details }`
  - `Column` = `{ id, title, cardIds[] }`
  - `BoardData` = `{ columns[], cards: Record<string, Card> }`
- `initialData` seeds five columns and starter cards.
- `moveCard(columns, activeId, overId)` handles:
  - Reorder within a column.
  - Move across columns.
  - Drop over a column container to append.
- `createId(prefix)` creates client-side IDs for new cards.

## Current test baseline

- Unit/component tests:
  - `src/components/KanbanBoard.test.tsx` covers render, rename, add, delete.
  - `src/lib/kanban.test.ts` covers move logic for reorder/move/append cases.
- E2E tests:
  - `tests/kanban.spec.ts` covers load, add card, drag between columns.
- Vitest config: `vitest.config.ts` (jsdom, setup file, coverage reporters configured).
- Playwright config: `playwright.config.ts` (runs dev server, Chromium project).

## Known constraints of current frontend

- No authentication yet (board is immediately visible).
- No backend integration yet (state resets on refresh).
- No persistence and no AI sidebar yet.
- No explicit coverage threshold gate configured yet in test tooling.

## Integration guidance for upcoming parts

- Keep frontend API interactions behind small client helper functions once backend arrives.
- Avoid coupling UI components directly to fetch calls; keep state orchestration in board-level container(s).
- Preserve `BoardData` JSON shape as the contract baseline unless explicitly migrated.
- Add tests as features land so unit coverage reaches and stays at 80%+.
