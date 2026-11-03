import contextlib
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[2] / "scripts"))
sys.path.insert(0, str(Path(__file__).parents[2] / "evals"))

from seed_db import CSV_DIR, seed


@pytest.fixture
def store_db(tmp_path):
    path = tmp_path / "emporio.sqlite"
    seed(path, CSV_DIR)
    return path


@pytest.fixture
def store_conn(store_db):
    with contextlib.closing(sqlite3.connect(store_db)) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        yield conn
