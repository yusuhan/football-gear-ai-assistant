"""Persistence for operations users, sessions and audit logs."""

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import uuid4

from app.core.security import create_session_token, hash_password, hash_session_token, verify_password
from app.db.client import DatabaseIntegrityError, DatabaseTarget, connect_database


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class OperationsRepository:
    """Authenticate support users and persist their sensitive actions."""

    def __init__(self, database_path: DatabaseTarget, session_hours: int = 8) -> None:
        self.database_path = database_path
        self.session_hours = session_hours

    def authenticate(self, username: str, password: str) -> Optional[dict[str, Any]]:
        user = self._fetch_one(
            """
            SELECT id, username, password_hash, role
            FROM operations_users
            WHERE username = ? AND is_active = 1
            """,
            [username],
        )
        if not user or not verify_password(password, user["password_hash"]):
            return None

        token = create_session_token()
        now = utc_now()
        expires_at = now + timedelta(hours=self.session_hours)
        self._execute(
            """
            INSERT INTO operations_sessions (id, user_id, token_hash, expires_at, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            [f"session_{uuid4().hex}", user["id"], hash_session_token(token), expires_at.isoformat(), now.isoformat()],
        )
        return {
            "access_token": token,
            "expires_at": expires_at.isoformat(),
            "operator": {"id": user["id"], "username": user["username"], "role": user["role"]},
        }

    def get_operator_by_session(self, token: str) -> Optional[dict[str, str]]:
        return self._fetch_one(
            """
            SELECT users.id, users.username, users.role, sessions.id AS session_id
            FROM operations_sessions AS sessions
            JOIN operations_users AS users ON users.id = sessions.user_id
            WHERE sessions.token_hash = ? AND sessions.expires_at > ? AND users.is_active = 1
            """,
            [hash_session_token(token), utc_now().isoformat()],
        )

    def revoke_session(self, token: str) -> None:
        self._execute("DELETE FROM operations_sessions WHERE token_hash = ?", [hash_session_token(token)])

    def list_users(self) -> list[dict[str, Any]]:
        """Return operations users without exposing password hashes."""

        return self._fetch_all(
            """
            SELECT id, username, role, is_active, created_at, updated_at
            FROM operations_users
            ORDER BY created_at ASC
            """,
            [],
        )

    def get_user(self, user_id: str) -> Optional[dict[str, Any]]:
        return self._fetch_one(
            """
            SELECT id, username, role, is_active, created_at, updated_at
            FROM operations_users WHERE id = ?
            """,
            [user_id],
        )

    def create_user(self, username: str, password: str, role: str) -> Optional[dict[str, Any]]:
        """Create an operations user, returning None for duplicate usernames."""

        user_id = f"ops_{uuid4().hex}"
        now = utc_now().isoformat()
        try:
            self._execute(
                """
                INSERT INTO operations_users (
                    id, username, password_hash, role, is_active, created_at, updated_at
                ) VALUES (?, ?, ?, ?, 1, ?, ?)
                """,
                [user_id, username, hash_password(password), role, now, now],
            )
        except DatabaseIntegrityError:
            return None
        return self.get_user(user_id)

    def update_user(self, user_id: str, role: str, is_active: bool) -> Optional[dict[str, Any]]:
        """Update role and active state, revoking sessions when access is removed."""

        if not self.get_user(user_id):
            return None
        self._execute(
            "UPDATE operations_users SET role = ?, is_active = ?, updated_at = ? WHERE id = ?",
            [role, int(is_active), utc_now().isoformat(), user_id],
        )
        if not is_active:
            self._execute("DELETE FROM operations_sessions WHERE user_id = ?", [user_id])
        return self.get_user(user_id)

    def count_active_admins(self) -> int:
        row = self._fetch_one(
            "SELECT COUNT(*) AS count FROM operations_users WHERE role = 'admin' AND is_active = 1",
            [],
        )
        return int(row["count"] if row else 0)

    def change_password(
        self,
        user_id: str,
        current_password: str,
        new_password: str,
        current_session_id: str,
    ) -> bool:
        """Change the current user's password and revoke their other sessions."""

        user = self._fetch_one(
            "SELECT password_hash FROM operations_users WHERE id = ? AND is_active = 1",
            [user_id],
        )
        if not user or not verify_password(current_password, user["password_hash"]):
            return False
        self._execute(
            "UPDATE operations_users SET password_hash = ?, updated_at = ? WHERE id = ?",
            [hash_password(new_password), utc_now().isoformat(), user_id],
        )
        self._execute(
            "DELETE FROM operations_sessions WHERE user_id = ? AND id != ?",
            [user_id, current_session_id],
        )
        return True

    def reset_password(self, user_id: str, new_password: str) -> bool:
        """Set a user's password and revoke all sessions for that user."""

        if not self.get_user(user_id):
            return False
        self._execute(
            "UPDATE operations_users SET password_hash = ?, updated_at = ? WHERE id = ?",
            [hash_password(new_password), utc_now().isoformat(), user_id],
        )
        self._execute("DELETE FROM operations_sessions WHERE user_id = ?", [user_id])
        return True

    def list_sessions(self, user_id: Optional[str] = None) -> list[dict[str, Any]]:
        """Return active sessions, optionally restricted to one user."""

        params: list[Any] = [utc_now().isoformat()]
        user_filter = ""
        if user_id:
            user_filter = "AND sessions.user_id = ?"
            params.append(user_id)
        return self._fetch_all(
            f"""
            SELECT sessions.id, users.id AS user_id, users.username, users.role,
                   sessions.expires_at, sessions.created_at
            FROM operations_sessions AS sessions
            JOIN operations_users AS users ON users.id = sessions.user_id
            WHERE sessions.expires_at > ? {user_filter}
            ORDER BY sessions.created_at DESC
            """,
            params,
        )

    def get_session(self, session_id: str) -> Optional[dict[str, Any]]:
        return self._fetch_one(
            "SELECT id, user_id FROM operations_sessions WHERE id = ?",
            [session_id],
        )

    def revoke_session_by_id(self, session_id: str) -> bool:
        if not self.get_session(session_id):
            return False
        self._execute("DELETE FROM operations_sessions WHERE id = ?", [session_id])
        return True

    def create_audit_log(
        self,
        actor: dict[str, str],
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        self._execute(
            """
            INSERT INTO audit_logs (
                id, actor_user_id, actor_username, actor_role, action,
                resource_type, resource_id, details_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                f"audit_{uuid4().hex}", actor["id"], actor["username"], actor["role"], action,
                resource_type, resource_id, json.dumps(details or {}, ensure_ascii=False), utc_now().isoformat(),
            ],
        )

    def list_audit_logs(self, limit: int = 100) -> list[dict[str, Any]]:
        rows = self._fetch_all(
            """
            SELECT id, actor_username, actor_role, action, resource_type, resource_id, details_json, created_at
            FROM audit_logs
            ORDER BY created_at DESC
            LIMIT ?
            """,
            [limit],
        )
        for row in rows:
            row["details"] = json.loads(row.pop("details_json"))
        return rows

    def _connect(self):
        return connect_database(self.database_path)

    def _execute(self, query: str, params: list[Any]) -> None:
        with self._connect() as connection:
            connection.execute(query, params)

    def _fetch_one(self, query: str, params: list[Any]) -> Optional[dict[str, Any]]:
        rows = self._fetch_all(query, params)
        return rows[0] if rows else None

    def _fetch_all(self, query: str, params: list[Any]) -> list[dict[str, Any]]:
        with self._connect() as connection:
            return [dict(row) for row in connection.execute(query, params).fetchall()]
