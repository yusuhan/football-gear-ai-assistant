"""Persistence repository for conversations, messages and Agent traces."""

import json
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from app.db.client import DatabaseTarget, connect_database


def utc_now() -> str:
    """Return an ISO timestamp suitable for SQLite text storage."""

    return datetime.now(timezone.utc).isoformat()


class ConversationRepository:
    """Store the customer support conversation lifecycle."""

    def __init__(self, database_path: DatabaseTarget) -> None:
        self.database_path = database_path

    def get_or_create_conversation(self, conversation_id: Optional[str], user_id: str, channel: str) -> str:
        """Return an existing conversation id or create a new active conversation."""

        if conversation_id and self._fetch_one("SELECT id FROM conversations WHERE id = ?", [conversation_id]):
            self.touch_conversation(conversation_id)
            return conversation_id

        new_id = conversation_id or f"conv_{uuid4().hex}"
        now = utc_now()
        self._execute(
            """
            INSERT INTO conversations (id, user_id, channel, status, created_at, updated_at)
            VALUES (?, ?, ?, 'active', ?, ?)
            """,
            [new_id, user_id, channel, now, now],
        )
        return new_id

    def get_channel_conversation(self, channel: str, external_conversation_id: str) -> Optional[str]:
        """Return the internal conversation id mapped to an external channel thread."""

        row = self._fetch_one(
            """
            SELECT conversation_id
            FROM channel_conversations
            WHERE channel = ? AND external_conversation_id = ?
            """,
            [channel, external_conversation_id],
        )
        return row["conversation_id"] if row else None

    def upsert_channel_conversation(
        self,
        channel: str,
        external_conversation_id: str,
        conversation_id: str,
    ) -> None:
        """Map a channel thread to an internal conversation id."""

        now = utc_now()
        self._execute(
            """
            INSERT INTO channel_conversations (
                channel, external_conversation_id, conversation_id, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(channel, external_conversation_id)
            DO UPDATE SET conversation_id = excluded.conversation_id, updated_at = excluded.updated_at
            """,
            [channel, external_conversation_id, conversation_id, now, now],
        )

    def touch_conversation(self, conversation_id: str) -> None:
        """Update a conversation's last activity timestamp."""

        self._execute("UPDATE conversations SET updated_at = ? WHERE id = ?", [utc_now(), conversation_id])

    def create_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        intent: Optional[str] = None,
        route: Optional[str] = None,
        confidence: Optional[float] = None,
    ) -> str:
        """Persist one user or assistant message."""

        message_id = f"msg_{uuid4().hex}"
        self._execute(
            """
            INSERT INTO messages (id, conversation_id, role, content, intent, route, confidence, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [message_id, conversation_id, role, content, intent, route, confidence, utc_now()],
        )
        self.touch_conversation(conversation_id)
        return message_id

    def create_tool_call_log(
        self,
        conversation_id: str,
        message_id: str,
        tool_name: str,
        arguments: dict[str, Any],
        result: dict[str, Any],
    ) -> None:
        """Persist a tool call made while producing an assistant message."""

        self._execute(
            """
            INSERT INTO tool_call_logs (id, conversation_id, message_id, tool_name, arguments_json, result_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                f"tool_{uuid4().hex}",
                conversation_id,
                message_id,
                tool_name,
                json.dumps(arguments, ensure_ascii=False),
                json.dumps(result, ensure_ascii=False),
                utc_now(),
            ],
        )

    def create_agent_event(
        self,
        conversation_id: str,
        event_type: str,
        payload: dict[str, Any],
        message_id: Optional[str] = None,
    ) -> None:
        """Persist structured Agent events such as routing and RAG sources."""

        self._execute(
            """
            INSERT INTO agent_events (id, conversation_id, message_id, event_type, payload_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                f"evt_{uuid4().hex}",
                conversation_id,
                message_id,
                event_type,
                json.dumps(payload, ensure_ascii=False),
                utc_now(),
            ],
        )

    def create_handoff_ticket(self, conversation_id: str, reason: str) -> dict[str, Any]:
        """Create an open handoff ticket and mark the conversation as waiting for a human."""

        existing_ticket = self.get_active_handoff_ticket(conversation_id)
        if existing_ticket:
            return existing_ticket

        ticket_id = f"handoff_{uuid4().hex}"
        now = utc_now()
        self._execute(
            """
            INSERT INTO handoff_tickets (id, conversation_id, reason, status, created_at, updated_at)
            VALUES (?, ?, ?, 'open', ?, ?)
            """,
            [ticket_id, conversation_id, reason, now, now],
        )
        self._execute(
            "UPDATE conversations SET status = 'needs_handoff', updated_at = ? WHERE id = ?",
            [now, conversation_id],
        )
        return {
            "id": ticket_id,
            "conversation_id": conversation_id,
            "reason": reason,
            "status": "open",
            "assigned_to": None,
            "resolution_note": None,
            "resolved_at": None,
            "created_at": now,
            "updated_at": now,
        }

    def get_active_handoff_ticket(self, conversation_id: str) -> Optional[dict[str, Any]]:
        """Return an open or in-progress handoff ticket for a conversation."""

        return self._fetch_one(
            """
            SELECT id, conversation_id, reason, status, assigned_to, resolution_note, resolved_at, created_at, updated_at
            FROM handoff_tickets
            WHERE conversation_id = ? AND status IN ('open', 'in_progress')
            ORDER BY created_at DESC
            LIMIT 1
            """,
            [conversation_id],
        )

    def list_handoff_tickets(self, status: Optional[str] = None) -> list[dict[str, Any]]:
        """Return handoff tickets, optionally filtered by status."""

        if status:
            return self._fetch_all(
                """
                SELECT id, conversation_id, reason, status, assigned_to, resolution_note, resolved_at, created_at, updated_at
                FROM handoff_tickets
                WHERE status = ?
                ORDER BY created_at DESC
                """,
                [status],
            )
        return self._fetch_all(
            """
            SELECT id, conversation_id, reason, status, assigned_to, resolution_note, resolved_at, created_at, updated_at
            FROM handoff_tickets
            ORDER BY created_at DESC
            """
        )

    def update_handoff_ticket(
        self,
        ticket_id: str,
        status: str,
        assigned_to: Optional[str] = None,
        resolution_note: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        """Update a handoff ticket and return the latest row."""

        existing_ticket = self._fetch_one(
            """
            SELECT id, conversation_id
            FROM handoff_tickets
            WHERE id = ?
            """,
            [ticket_id],
        )
        if not existing_ticket:
            return None

        now = utc_now()
        resolved_at = now if status == "resolved" else None
        self._execute(
            """
            UPDATE handoff_tickets
            SET status = ?, assigned_to = ?, resolution_note = ?, resolved_at = ?, updated_at = ?
            WHERE id = ?
            """,
            [status, assigned_to, resolution_note, resolved_at, now, ticket_id],
        )

        conversation_status = "active" if status == "resolved" else "needs_handoff"
        self._execute(
            "UPDATE conversations SET status = ?, updated_at = ? WHERE id = ?",
            [conversation_status, now, existing_ticket["conversation_id"]],
        )
        return self.get_handoff_ticket(ticket_id)

    def get_handoff_ticket(self, ticket_id: str) -> Optional[dict[str, Any]]:
        """Return one handoff ticket by id."""

        return self._fetch_one(
            """
            SELECT id, conversation_id, reason, status, assigned_to, resolution_note, resolved_at, created_at, updated_at
            FROM handoff_tickets
            WHERE id = ?
            """,
            [ticket_id],
        )

    def list_messages(self, conversation_id: str) -> list[dict[str, Any]]:
        """Return messages in chronological order."""

        return self._fetch_all(
            """
            SELECT id, conversation_id, role, content, intent, route, confidence, created_at
            FROM messages
            WHERE conversation_id = ?
            ORDER BY created_at ASC
            """,
            [conversation_id],
        )

    def count_conversations(self) -> int:
        """Count persisted conversations."""

        return int(self._fetch_one("SELECT COUNT(*) AS count FROM conversations")["count"])

    def count_open_handoffs(self) -> int:
        """Count open human handoff tickets."""

        return int(self._fetch_one("SELECT COUNT(*) AS count FROM handoff_tickets WHERE status = 'open'")["count"])

    def _connect(self):
        """Open a database connection with dictionary-like rows."""

        return connect_database(self.database_path)

    def _execute(self, query: str, params: list[Any]) -> None:
        """Execute one write query."""

        with self._connect() as connection:
            connection.execute(query, params)

    def _fetch_one(self, query: str, params: Optional[list[Any]] = None) -> Optional[dict[str, Any]]:
        """Fetch one row as a dictionary, or None."""

        rows = self._fetch_all(query, params)
        return rows[0] if rows else None

    def _fetch_all(self, query: str, params: Optional[list[Any]] = None) -> list[dict[str, Any]]:
        """Fetch rows as plain dictionaries."""

        with self._connect() as connection:
            cursor = connection.execute(query, params or [])
            return [dict(row) for row in cursor.fetchall()]
