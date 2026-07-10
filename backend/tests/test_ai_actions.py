from ai_actions import apply_board_operations, validate_ai_actions_payload
from db import default_board


def test_validate_ai_actions_payload_requires_assistant_message() -> None:
    try:
        validate_ai_actions_payload({"operations": []})
        assert False, "Expected ValueError"
    except ValueError as error:
        assert "assistantMessage" in str(error)


def test_apply_board_operations_handles_rename_create_edit_move_delete() -> None:
    board = default_board()
    operations = [
        {"type": "rename_column", "columnId": "col-backlog", "title": "Ideas"},
        {
            "type": "create_card",
            "columnId": "col-backlog",
            "cardId": "card-99",
            "title": "Draft launch copy",
            "details": "Create v1 headline options.",
        },
        {
            "type": "edit_card",
            "cardId": "card-99",
            "title": "Draft launch homepage copy",
        },
        {
            "type": "move_card",
            "cardId": "card-99",
            "toColumnId": "col-progress",
            "index": 0,
        },
        {
            "type": "delete_card",
            "cardId": "card-99",
        },
    ]

    next_board, applied = apply_board_operations(board, operations)

    assert applied == operations
    renamed = [c for c in next_board["columns"] if c["id"] == "col-backlog"][0]
    assert renamed["title"] == "Ideas"
    assert "card-99" not in next_board["cards"]


def test_apply_board_operations_rejects_unknown_operation() -> None:
    board = default_board()

    try:
        apply_board_operations(board, [{"type": "explode_board"}])
        assert False, "Expected ValueError"
    except ValueError as error:
        assert "Unsupported operation type" in str(error)
