import copy
from typing import Any


def validate_ai_actions_payload(payload: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    assistant_message = payload.get("assistantMessage")
    operations = payload.get("operations", [])

    if not isinstance(assistant_message, str) or not assistant_message.strip():
        raise ValueError("assistantMessage must be a non-empty string")
    if not isinstance(operations, list):
        raise ValueError("operations must be a list")

    return assistant_message.strip(), operations


def apply_board_operations(
    board: dict[str, Any],
    operations: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    next_board = copy.deepcopy(board)
    columns = next_board.get("columns")
    cards = next_board.get("cards")

    if not isinstance(columns, list) or not isinstance(cards, dict):
        raise ValueError("Board shape is invalid")

    for operation in operations:
        if not isinstance(operation, dict):
            raise ValueError("Each operation must be an object")

        op_type = operation.get("type")
        if not isinstance(op_type, str):
            raise ValueError("Operation type is required")

        if op_type == "rename_column":
            _apply_rename_column(columns, operation)
        elif op_type == "create_card":
            _apply_create_card(columns, cards, operation)
        elif op_type == "edit_card":
            _apply_edit_card(cards, operation)
        elif op_type == "move_card":
            _apply_move_card(columns, cards, operation)
        elif op_type == "delete_card":
            _apply_delete_card(columns, cards, operation)
        else:
            raise ValueError(f"Unsupported operation type: {op_type}")

    return next_board, operations


def _find_column(columns: list[dict[str, Any]], column_id: str) -> dict[str, Any]:
    for column in columns:
        if column.get("id") == column_id:
            return column
    raise ValueError(f"Column not found: {column_id}")


def _find_column_containing_card(
    columns: list[dict[str, Any]],
    card_id: str,
) -> dict[str, Any]:
    for column in columns:
        card_ids = column.get("cardIds")
        if isinstance(card_ids, list) and card_id in card_ids:
            return column
    raise ValueError(f"Card not found in any column: {card_id}")


def _apply_rename_column(columns: list[dict[str, Any]], operation: dict[str, Any]) -> None:
    column_id = operation.get("columnId")
    title = operation.get("title")

    if not isinstance(column_id, str) or not column_id:
        raise ValueError("rename_column requires columnId")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("rename_column requires non-empty title")

    column = _find_column(columns, column_id)
    column["title"] = title.strip()


def _apply_create_card(
    columns: list[dict[str, Any]],
    cards: dict[str, Any],
    operation: dict[str, Any],
) -> None:
    column_id = operation.get("columnId")
    card_id = operation.get("cardId")
    title = operation.get("title")
    details = operation.get("details", "")

    if not isinstance(column_id, str) or not column_id:
        raise ValueError("create_card requires columnId")
    if not isinstance(card_id, str) or not card_id:
        raise ValueError("create_card requires cardId")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("create_card requires non-empty title")
    if not isinstance(details, str):
        raise ValueError("create_card details must be a string")
    if card_id in cards:
        raise ValueError(f"Card already exists: {card_id}")

    column = _find_column(columns, column_id)
    card_ids = column.get("cardIds")
    if not isinstance(card_ids, list):
        raise ValueError(f"Column cardIds must be a list: {column_id}")

    cards[card_id] = {
        "id": card_id,
        "title": title.strip(),
        "details": details,
    }
    card_ids.append(card_id)


def _apply_edit_card(cards: dict[str, Any], operation: dict[str, Any]) -> None:
    card_id = operation.get("cardId")
    if not isinstance(card_id, str) or not card_id:
        raise ValueError("edit_card requires cardId")
    if card_id not in cards:
        raise ValueError(f"Card not found: {card_id}")

    title = operation.get("title")
    details = operation.get("details")

    if title is None and details is None:
        raise ValueError("edit_card requires title and/or details")
    if title is not None:
        if not isinstance(title, str) or not title.strip():
            raise ValueError("edit_card title must be non-empty when provided")
        cards[card_id]["title"] = title.strip()
    if details is not None:
        if not isinstance(details, str):
            raise ValueError("edit_card details must be a string when provided")
        cards[card_id]["details"] = details


def _apply_move_card(
    columns: list[dict[str, Any]],
    cards: dict[str, Any],
    operation: dict[str, Any],
) -> None:
    card_id = operation.get("cardId")
    to_column_id = operation.get("toColumnId")
    index = operation.get("index")

    if not isinstance(card_id, str) or not card_id:
        raise ValueError("move_card requires cardId")
    if not isinstance(to_column_id, str) or not to_column_id:
        raise ValueError("move_card requires toColumnId")
    if card_id not in cards:
        raise ValueError(f"Card not found: {card_id}")
    if index is not None and not isinstance(index, int):
        raise ValueError("move_card index must be an integer when provided")

    from_column = _find_column_containing_card(columns, card_id)
    to_column = _find_column(columns, to_column_id)

    from_ids = from_column.get("cardIds")
    to_ids = to_column.get("cardIds")
    if not isinstance(from_ids, list) or not isinstance(to_ids, list):
        raise ValueError("Column cardIds must be lists")

    from_ids.remove(card_id)
    insert_at = len(to_ids) if index is None else max(0, min(index, len(to_ids)))
    to_ids.insert(insert_at, card_id)


def _apply_delete_card(
    columns: list[dict[str, Any]],
    cards: dict[str, Any],
    operation: dict[str, Any],
) -> None:
    card_id = operation.get("cardId")
    if not isinstance(card_id, str) or not card_id:
        raise ValueError("delete_card requires cardId")
    if card_id not in cards:
        raise ValueError(f"Card not found: {card_id}")

    for column in columns:
        card_ids = column.get("cardIds")
        if isinstance(card_ids, list) and card_id in card_ids:
            card_ids.remove(card_id)

    del cards[card_id]
