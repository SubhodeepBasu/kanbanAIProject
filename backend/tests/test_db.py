import sqlite3
from pathlib import Path

from db import default_board, get_user_board, init_database, save_user_board


def test_init_database_creates_tables_and_default_user_board(tmp_path: Path) -> None:
    db_file = tmp_path / "pm.db"

    init_database(db_file)

    assert db_file.exists()
    with sqlite3.connect(str(db_file)) as connection:
        table_names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    assert "users" in table_names
    assert "boards" in table_names

    board_data = get_user_board(db_file, "user")
    assert board_data is not None
    assert board_data["board"] == default_board()


def test_save_user_board_persists_updates(tmp_path: Path) -> None:
    db_file = tmp_path / "pm.db"
    init_database(db_file)

    updated_board = {
        "columns": [{"id": "col-backlog", "title": "Backlog", "cardIds": []}],
        "cards": {},
    }
    result = save_user_board(db_file, "user", updated_board)

    assert result is not None
    assert result["board"] == updated_board
    stored = get_user_board(db_file, "user")
    assert stored is not None
    assert stored["board"] == updated_board


def test_save_user_board_returns_none_for_unknown_user(tmp_path: Path) -> None:
    db_file = tmp_path / "pm.db"
    init_database(db_file)

    result = save_user_board(
        db_file,
        "missing",
        {"columns": [], "cards": {}},
    )

    assert result is None
