import type { BoardData } from "@/lib/kanban";

type BoardResponse = {
  username: string;
  board: BoardData;
  updatedAt: string;
};

export type AiBoardResponse = {
  status: string;
  username: string;
  assistantMessage: string;
  operationsApplied: Array<Record<string, unknown>>;
  board: BoardData;
  updatedAt: string;
  model: string;
  requestedModel: string;
  fallbackUsed: boolean;
};

const BOARD_PATH = "/api/board?username=user";
const AI_BOARD_PATH = "/api/ai/board?username=user&model=openai/gpt-4o-mini";

export const fetchBoard = async (): Promise<BoardData> => {
  const response = await fetch(BOARD_PATH, { cache: "no-store" });
  if (!response.ok) {
    throw new Error("Failed to load board");
  }
  const payload = (await response.json()) as BoardResponse;
  return payload.board;
};

export const saveBoard = async (board: BoardData): Promise<void> => {
  const response = await fetch(BOARD_PATH, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ board }),
  });
  if (!response.ok) {
    throw new Error("Failed to save board");
  }
};

export const requestAiBoardAction = async (prompt: string): Promise<AiBoardResponse> => {
  const response = await fetch(AI_BOARD_PATH, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt }),
  });

  if (!response.ok) {
    throw new Error("Failed to run AI board action");
  }

  return (await response.json()) as AiBoardResponse;
};
