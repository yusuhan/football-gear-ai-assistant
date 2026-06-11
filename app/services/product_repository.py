"""Repository for product, inventory and size-guide queries."""

import sqlite3
from pathlib import Path
from typing import Any, Optional


class ProductRepository:
    """Small SQLite repository used by Agent tools."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def list_products(self) -> list[dict[str, Any]]:
        """Return all products ordered by price."""

        return self._fetch_all("SELECT * FROM products ORDER BY price ASC")

    def list_inventory(self) -> list[dict[str, Any]]:
        """Return inventory rows joined with product names."""

        return self._fetch_all(
            """
            SELECT inventory.product_id, products.name AS product_name, inventory.size, inventory.stock
            FROM inventory
            JOIN products ON products.id = inventory.product_id
            ORDER BY products.name ASC, inventory.size ASC
            """
        )

    def count_products(self) -> int:
        """Count product catalog rows."""

        return int(self._fetch_one("SELECT COUNT(*) AS count FROM products")["count"])

    def count_inventory_rows(self) -> int:
        """Count inventory rows."""

        return int(self._fetch_one("SELECT COUNT(*) AS count FROM inventory")["count"])

    def search_products(self, position: Optional[str], budget: Optional[int]) -> list[dict[str, Any]]:
        """Find products by football position and budget."""

        conditions = []
        params: list[Any] = []
        if budget is not None:
            conditions.append("price <= ?")
            params.append(budget)
        if position:
            conditions.append("lower(recommended_position) LIKE ?")
            params.append(f"%{position.lower()}%")
        else:
            # A generic "recommend football boots" request should not surface
            # goalkeeper gloves or protective gear ahead of boots.
            conditions.append("category = ?")
            params.append("football_boots")

        where_sql = " AND ".join(conditions)
        query = f"SELECT * FROM products WHERE {where_sql} ORDER BY price ASC LIMIT 5"
        return self._fetch_all(query, params)

    def check_inventory(self, product_name: str, size: int) -> Optional[dict[str, Any]]:
        """Return stock for the best product name match and size."""

        rows = self._fetch_all(
            """
            SELECT products.id AS product_id, products.name AS product_name, inventory.size, inventory.stock
            FROM inventory
            JOIN products ON products.id = inventory.product_id
            WHERE lower(products.name) LIKE ? AND inventory.size = ?
            ORDER BY inventory.stock DESC
            LIMIT 1
            """,
            [f"%{product_name.lower()}%", size],
        )
        return rows[0] if rows else None

    def get_size_recommendation(self, foot_length: float) -> Optional[dict[str, Any]]:
        """Return the nearest size guide row for a foot length in centimeters."""

        rows = self._fetch_all(
            """
            SELECT foot_length, recommended_size
            FROM size_guide
            ORDER BY ABS(foot_length - ?)
            LIMIT 1
            """,
            [foot_length],
        )
        return rows[0] if rows else None

    def _connect(self) -> sqlite3.Connection:
        """Open a SQLite connection with dictionary-like rows."""

        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _fetch_one(self, query: str, params: Optional[list[Any]] = None) -> dict[str, Any]:
        """Fetch one row as a plain dictionary."""

        rows = self._fetch_all(query, params)
        return rows[0]

    def _fetch_all(self, query: str, params: Optional[list[Any]] = None) -> list[dict[str, Any]]:
        """Fetch many rows as plain dictionaries."""

        with self._connect() as connection:
            cursor = connection.execute(query, params or [])
            return [dict(row) for row in cursor.fetchall()]
