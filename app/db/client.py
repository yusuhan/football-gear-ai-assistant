"""Small database adapter supporting local SQLite and hosted PostgreSQL."""

import sqlite3
from pathlib import Path
from typing import Any, Iterable, Union

import psycopg
from psycopg.rows import dict_row

DatabaseTarget = Union[str, Path]
DatabaseIntegrityError = (sqlite3.IntegrityError, psycopg.IntegrityError)


def is_postgres(target: DatabaseTarget) -> bool:
    """Return whether a database target is a PostgreSQL connection URL."""

    return str(target).startswith(("postgres://", "postgresql://"))


class DatabaseConnection:
    """Normalize connection and placeholder behavior across both databases."""

    def __init__(self, target: DatabaseTarget) -> None:
        self.postgres = is_postgres(target)
        if self.postgres:
            self.raw = psycopg.connect(str(target), row_factory=dict_row)
        else:
            connection = sqlite3.connect(Path(target))
            connection.row_factory = sqlite3.Row
            self.raw = connection

    def __enter__(self) -> "DatabaseConnection":
        self.raw.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.raw.__exit__(exc_type, exc_value, traceback)

    def execute(self, query: str, params: Iterable[Any] = ()):
        return self.raw.execute(self._adapt_query(query), list(params))

    def executemany(self, query: str, params: Iterable[Iterable[Any]]):
        adapted_query = self._adapt_query(query)
        if self.postgres:
            cursor = self.raw.cursor()
            cursor.executemany(adapted_query, params)
            return cursor
        return self.raw.executemany(adapted_query, params)

    def executescript(self, script: str) -> None:
        if not self.postgres:
            self.raw.executescript(script)
            return
        for statement in script.split(";"):
            if statement.strip():
                self.raw.execute(statement)

    def _adapt_query(self, query: str) -> str:
        return query.replace("?", "%s") if self.postgres else query


def connect_database(target: DatabaseTarget) -> DatabaseConnection:
    """Open a database connection for a path or PostgreSQL URL."""

    return DatabaseConnection(target)
