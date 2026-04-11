"""Test fixtures for Chores."""

import os
import sys
import sqlite3
import pytest

# Ensure app modules are importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """Create a temporary SQLite database for testing."""
    db_path = str(tmp_path / "test_chores.db")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))

    import database
    database._conn = None
    database.DB_PATH = db_path
    database.initialize()
    yield database.get_connection()
    database.close_connection()
