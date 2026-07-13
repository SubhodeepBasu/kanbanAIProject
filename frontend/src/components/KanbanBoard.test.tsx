import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { KanbanBoard } from "@/components/KanbanBoard";
import { initialData } from "@/lib/kanban";

const fetchBoardMock = vi.fn();
const saveBoardMock = vi.fn();
const requestAiBoardActionMock = vi.fn();

vi.mock("@/lib/api", () => ({
  fetchBoard: () => fetchBoardMock(),
  saveBoard: (board: unknown) => saveBoardMock(board),
  requestAiBoardAction: (prompt: string) => requestAiBoardActionMock(prompt),
}));

const getFirstColumn = () => screen.getAllByTestId(/column-/i)[0];

describe("KanbanBoard", () => {
  beforeEach(() => {
    fetchBoardMock.mockResolvedValue(initialData);
    saveBoardMock.mockResolvedValue(undefined);
    requestAiBoardActionMock.mockReset();
  });

  it("renders five columns", async () => {
    render(<KanbanBoard />);
    expect(await screen.findAllByTestId(/column-/i)).toHaveLength(5);
  });

  it("renames a column", async () => {
    render(<KanbanBoard />);
    const column = getFirstColumn();
    const input = within(column).getByLabelText("Column title");
    await userEvent.click(input);
    await userEvent.keyboard("{Control>}a{/Control}");
    await userEvent.keyboard("{Backspace}");
    await userEvent.type(input, "New Name");
    expect(input).toHaveValue("New Name");
    expect(saveBoardMock).toHaveBeenCalled();
  });

  it("adds and removes a card", async () => {
    render(<KanbanBoard />);
    const column = getFirstColumn();
    const addButton = within(column).getByRole("button", {
      name: /add a card/i,
    });
    await userEvent.click(addButton);

    const titleInput = within(column).getByPlaceholderText(/card title/i);
    await userEvent.type(titleInput, "New card");
    const detailsInput = within(column).getByPlaceholderText(/details/i);
    await userEvent.type(detailsInput, "Notes");

    await userEvent.click(within(column).getByRole("button", { name: /add card/i }));

    expect(within(column).getByText("New card")).toBeInTheDocument();

    const deleteButton = within(column).getByRole("button", {
      name: /delete new card/i,
    });
    await userEvent.click(deleteButton);

    expect(within(column).queryByText("New card")).not.toBeInTheDocument();
  });

  it("ignores board edits attempted before the initial fetch resolves", async () => {
    let resolveFetch: (board: typeof initialData) => void = () => {};
    fetchBoardMock.mockReturnValueOnce(
      new Promise<typeof initialData>((resolve) => {
        resolveFetch = resolve;
      })
    );

    render(<KanbanBoard />);
    saveBoardMock.mockClear();
    const column = getFirstColumn();
    const input = within(column).getByLabelText("Column title");
    await userEvent.click(input);
    await userEvent.type(input, "X");

    expect(saveBoardMock).not.toHaveBeenCalled();

    resolveFetch(initialData);
    await waitFor(() =>
      expect(screen.queryByText(/loading board/i)).not.toBeInTheDocument()
    );
  });

  it("shows backend load error if board fetch fails", async () => {
    fetchBoardMock.mockRejectedValueOnce(new Error("boom"));
    render(<KanbanBoard />);
    expect(
      await screen.findByText("Could not load board from backend. Showing local board.")
    ).toBeInTheDocument();
  });

  it("sends prompt to AI and renders assistant reply", async () => {
    requestAiBoardActionMock.mockResolvedValueOnce({
      status: "ok",
      username: "user",
      assistantMessage: "Renamed the backlog column.",
      operationsApplied: [{ type: "rename_column" }],
      board: {
        ...initialData,
        columns: initialData.columns.map((column) =>
          column.id === "col-backlog" ? { ...column, title: "Ideas" } : column
        ),
      },
      updatedAt: "now",
      model: "qwen/qwen3-coder:free",
      requestedModel: "qwen/qwen3-coder:free",
      fallbackUsed: false,
    });

    render(<KanbanBoard />);

    await userEvent.type(
      screen.getByPlaceholderText("Ask AI to update this board"),
      "Rename backlog to ideas"
    );
    await userEvent.click(screen.getByRole("button", { name: "Send to AI" }));

    expect(await screen.findByText("Renamed the backlog column.")).toBeInTheDocument();
    expect(screen.getAllByText("Ideas").length).toBeGreaterThan(0);
    expect(requestAiBoardActionMock).toHaveBeenCalledWith("Rename backlog to ideas");
  });

  it("shows AI error and keeps board stable if AI request fails", async () => {
    requestAiBoardActionMock.mockRejectedValueOnce(new Error("fail"));

    render(<KanbanBoard />);

    await userEvent.type(
      screen.getByPlaceholderText("Ask AI to update this board"),
      "Move card-1 to done"
    );
    await userEvent.click(screen.getByRole("button", { name: "Send to AI" }));

    expect(
      await screen.findByText("AI request failed. Your board has not been changed.")
    ).toBeInTheDocument();
    expect(screen.getAllByTestId(/column-/i)).toHaveLength(5);
  });
});
