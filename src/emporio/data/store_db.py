import contextlib
import sqlite3
from collections.abc import Iterator
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[3] / "data" / "emporio.sqlite"


@contextlib.contextmanager
def read_connection(path: Path = DB_PATH) -> Iterator[sqlite3.Connection]:
    with contextlib.closing(sqlite3.connect(f"file:{path}?mode=ro", uri=True)) as conn:
        conn.row_factory = sqlite3.Row
        yield conn


@contextlib.contextmanager
def write_connection(path: Path = DB_PATH) -> Iterator[sqlite3.Connection]:
    with contextlib.closing(sqlite3.connect(path)) as conn, conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        yield conn
