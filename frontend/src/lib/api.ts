import type { BoardData } from "@/lib/kanban";

type BoardResponse = {
  username: string;
  board: BoardData;
  updatedAt: string;
};

const BOARD_PATH = "/api/board?username=user";

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
