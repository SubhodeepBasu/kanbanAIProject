from ai_actions import apply_board_operations, is_valid_board_shape, validate_ai_actions_payload
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


def test_is_valid_board_shape_rejects_dangling_card_reference() -> None:
    board = {
        "columns": [{"id": "col-backlog", "title": "Backlog", "cardIds": ["ghost-card"]}],
        "cards": {},
    }

    assert is_valid_board_shape(board) is False


def test_is_valid_board_shape_rejects_duplicate_card_reference() -> None:
    board = {
        "columns": [
            {"id": "col-a", "title": "A", "cardIds": ["card-1"]},
            {"id": "col-b", "title": "B", "cardIds": ["card-1"]},
        ],
        "cards": {"card-1": {"id": "card-1", "title": "T", "details": "D"}},
    }

    assert is_valid_board_shape(board) is False


def test_is_valid_board_shape_accepts_default_board() -> None:
    assert is_valid_board_shape(default_board()) is True


def test_apply_board_operations_rejects_invalid_input_board_shape() -> None:
    bad_board = {
        "columns": [{"id": "col-backlog", "title": "Backlog", "cardIds": ["ghost-card"]}],
        "cards": {},
    }

    try:
        apply_board_operations(bad_board, [])
        assert False, "Expected ValueError"
    except ValueError as error:
        assert "invalid" in str(error).lower()
