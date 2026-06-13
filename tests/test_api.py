"""API tests for the FastAPI application."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import create_app


class APITest(unittest.TestCase):
    """Validate HTTP endpoints used by the demo frontend."""

    def setUp(self) -> None:
        self.temp_directory = TemporaryDirectory()
        database_path = str(Path(self.temp_directory.name) / "test.db")
        with patch.dict("os.environ", {"DATABASE_PATH": database_path, "DATABASE_URL": ""}):
            app = create_app()
        self.client = TestClient(app)
        self.settings = app.state.settings
        login_response = self.client.post(
            "/admin/auth/login",
            json={"username": self.settings.admin_username, "password": self.settings.admin_password},
        )
        self.admin_token = login_response.json()["access_token"]
        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}

    def tearDown(self) -> None:
        self.temp_directory.cleanup()

    def login_support(self) -> dict:
        response = self.client.post(
            "/admin/auth/login",
            json={"username": self.settings.support_username, "password": self.settings.support_password},
        )
        self.assertEqual(response.status_code, 200)
        return response.json()

    def create_operator(self, role: str = "support") -> tuple[dict, str]:
        username = f"user_{uuid4().hex[:10]}"
        password = "initial-password"
        response = self.client.post(
            "/admin/users",
            headers=self.admin_headers,
            json={"username": username, "password": password, "role": role},
        )
        self.assertEqual(response.status_code, 201)
        return response.json(), password

    def test_health(self) -> None:
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertEqual(response.json()["faq_articles"], 20)
        self.assertIn("conversations", response.json())
        self.assertIn("open_handoffs", response.json())

    def test_chat_inventory(self) -> None:
        response = self.client.post("/chat", json={"message": "Mercurial 16 Elite有43码吗"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["route"], "tool")
        self.assertTrue(response.json()["conversation_id"].startswith("conv_"))

    def test_products(self) -> None:
        response = self.client.get("/products")

        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.json()), 8)

    def test_chat_persists_conversation_messages(self) -> None:
        chat_response = self.client.post("/chat", json={"message": "多久发货"})
        conversation_id = chat_response.json()["conversation_id"]

        history_response = self.client.get(
            f"/conversations/{conversation_id}/messages",
            headers=self.admin_headers,
        )

        self.assertEqual(history_response.status_code, 200)
        self.assertEqual([message["role"] for message in history_response.json()], ["user", "assistant"])

    def test_sensitive_message_creates_handoff_ticket(self) -> None:
        chat_response = self.client.post("/chat", json={"message": "我要投诉并退款"})

        self.assertEqual(chat_response.status_code, 200)
        self.assertTrue(chat_response.json()["needs_handoff"])
        self.assertTrue(chat_response.json()["handoff"]["ticket_id"].startswith("handoff_"))

        tickets_response = self.client.get("/handoff-tickets", headers=self.admin_headers)

        self.assertEqual(tickets_response.status_code, 200)
        self.assertGreaterEqual(len(tickets_response.json()), 1)

    def test_repeated_sensitive_messages_reuse_open_handoff_ticket(self) -> None:
        first_response = self.client.post("/chat", json={"message": "我要投诉"})
        conversation_id = first_response.json()["conversation_id"]
        first_ticket_id = first_response.json()["handoff"]["ticket_id"]

        second_response = self.client.post(
            "/chat",
            json={"conversation_id": conversation_id, "message": "我还要退款"},
        )

        self.assertEqual(second_response.json()["handoff"]["ticket_id"], first_ticket_id)
        self.assertEqual(second_response.json()["route"], "handoff")
        self.assertEqual(second_response.json()["intent"], "human_handoff")

    def test_identity_question_does_not_create_handoff(self) -> None:
        response = self.client.post("/chat", json={"message": "你是谁"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["intent"], "assistant_identity")
        self.assertFalse(response.json()["needs_handoff"])

    def test_identity_question_is_answered_during_active_handoff(self) -> None:
        first_response = self.client.post("/chat", json={"message": "我要投诉"})
        conversation_id = first_response.json()["conversation_id"]

        identity_response = self.client.post(
            "/chat",
            json={"conversation_id": conversation_id, "message": "你是谁"},
        )
        business_response = self.client.post(
            "/chat",
            json={"conversation_id": conversation_id, "message": "多久发货"},
        )

        self.assertEqual(identity_response.json()["intent"], "assistant_identity")
        self.assertEqual(identity_response.json()["route"], "self_service")
        self.assertEqual(business_response.json()["route"], "handoff")

    def test_unknown_question_asks_for_context_without_handoff(self) -> None:
        response = self.client.post("/chat", json={"message": "你觉得怎么样"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["route"], "fallback")
        self.assertFalse(response.json()["needs_handoff"])

    def test_channel_message_reuses_external_conversation_mapping(self) -> None:
        payload = {
            "external_user_id": "buyer_001",
            "external_conversation_id": "taobao_thread_001",
            "message": "多久发货",
        }
        first_response = self.client.post("/channels/taobao/messages", json=payload)
        second_response = self.client.post(
            "/channels/taobao/messages",
            json={**payload, "message": "支持退货吗"},
        )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(first_response.json()["conversation_id"], second_response.json()["conversation_id"])
        self.assertEqual(first_response.json()["channel"], "taobao")

    def test_handoff_ticket_can_be_resolved(self) -> None:
        chat_response = self.client.post("/chat", json={"message": "我要投诉"})
        ticket_id = chat_response.json()["handoff"]["ticket_id"]

        update_response = self.client.patch(
            f"/handoff-tickets/{ticket_id}",
            headers=self.admin_headers,
            json={
                "status": "resolved",
                "assigned_to": "agent_001",
                "resolution_note": "已人工联系用户处理",
            },
        )

        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["status"], "resolved")
        self.assertEqual(update_response.json()["assigned_to"], self.settings.admin_username)
        self.assertIsNotNone(update_response.json()["resolved_at"])

    def test_resolved_handoff_allows_ai_again(self) -> None:
        first_response = self.client.post("/chat", json={"message": "我要投诉"})
        conversation_id = first_response.json()["conversation_id"]
        ticket_id = first_response.json()["handoff"]["ticket_id"]
        self.client.patch(
            f"/handoff-tickets/{ticket_id}",
            headers=self.admin_headers,
            json={"status": "resolved", "assigned_to": "agent_001", "resolution_note": "done"},
        )

        next_response = self.client.post(
            "/chat",
            json={"conversation_id": conversation_id, "message": "多久发货"},
        )

        self.assertEqual(next_response.json()["route"], "rag")
        self.assertFalse(next_response.json()["needs_handoff"])

    def test_operations_endpoints_require_admin_token(self) -> None:
        self.assertEqual(self.client.get("/handoff-tickets").status_code, 401)
        self.assertEqual(self.client.get("/conversations/unknown/messages").status_code, 401)

    def test_admin_login_validates_token(self) -> None:
        invalid_response = self.client.post(
            "/admin/auth/login",
            json={"username": self.settings.admin_username, "password": "wrong"},
        )
        valid_response = self.client.post(
            "/admin/auth/login",
            json={"username": self.settings.admin_username, "password": self.settings.admin_password},
        )

        self.assertEqual(invalid_response.status_code, 401)
        self.assertEqual(valid_response.status_code, 200)
        self.assertEqual(valid_response.json()["operator"]["role"], "admin")
        self.assertTrue(valid_response.json()["access_token"])

    def test_support_can_update_ticket_but_cannot_read_audit_logs(self) -> None:
        support_session = self.login_support()
        support_headers = {"Authorization": f"Bearer {support_session['access_token']}"}
        ticket_id = self.client.post("/chat", json={"message": "我要投诉"}).json()["handoff"]["ticket_id"]

        update_response = self.client.patch(
            f"/handoff-tickets/{ticket_id}",
            headers=support_headers,
            json={"status": "in_progress", "assigned_to": "forged_name"},
        )
        audit_response = self.client.get("/admin/audit-logs", headers=support_headers)

        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["assigned_to"], self.settings.support_username)
        self.assertEqual(audit_response.status_code, 403)

    def test_admin_can_read_handoff_audit_log(self) -> None:
        ticket_id = self.client.post("/chat", json={"message": "我要投诉"}).json()["handoff"]["ticket_id"]
        self.client.patch(
            f"/handoff-tickets/{ticket_id}",
            headers=self.admin_headers,
            json={"status": "resolved", "resolution_note": "人工处理完成"},
        )

        response = self.client.get("/admin/audit-logs", headers=self.admin_headers)

        self.assertEqual(response.status_code, 200)
        matching_logs = [log for log in response.json() if log["resource_id"] == ticket_id]
        self.assertEqual(matching_logs[0]["action"], "handoff.update")
        self.assertEqual(matching_logs[0]["actor_username"], self.settings.admin_username)

    def test_logout_revokes_operations_session(self) -> None:
        logout_response = self.client.post("/admin/auth/logout", headers=self.admin_headers)
        tickets_response = self.client.get("/handoff-tickets", headers=self.admin_headers)

        self.assertEqual(logout_response.status_code, 204)
        self.assertEqual(tickets_response.status_code, 401)

    def test_admin_can_create_and_deactivate_support_user(self) -> None:
        user, _ = self.create_operator()

        update_response = self.client.patch(
            f"/admin/users/{user['id']}",
            headers=self.admin_headers,
            json={"role": "support", "is_active": False},
        )
        users_response = self.client.get("/admin/users", headers=self.admin_headers)

        self.assertEqual(update_response.status_code, 200)
        self.assertFalse(update_response.json()["is_active"])
        self.assertIn(user["id"], [item["id"] for item in users_response.json()])

    def test_admin_cannot_remove_own_access(self) -> None:
        response = self.client.patch(
            "/admin/users/ops_admin",
            headers=self.admin_headers,
            json={"role": "support", "is_active": True},
        )

        self.assertEqual(response.status_code, 400)

    def test_password_change_revokes_other_sessions(self) -> None:
        user, initial_password = self.create_operator()
        first_login = self.client.post(
            "/admin/auth/login",
            json={"username": user["username"], "password": initial_password},
        ).json()
        second_login = self.client.post(
            "/admin/auth/login",
            json={"username": user["username"], "password": initial_password},
        ).json()
        first_headers = {"Authorization": f"Bearer {first_login['access_token']}"}
        second_headers = {"Authorization": f"Bearer {second_login['access_token']}"}

        change_response = self.client.post(
            "/admin/auth/change-password",
            headers=first_headers,
            json={"current_password": initial_password, "new_password": "updated-password"},
        )

        self.assertEqual(change_response.status_code, 204)
        self.assertEqual(self.client.get("/handoff-tickets", headers=first_headers).status_code, 200)
        self.assertEqual(self.client.get("/handoff-tickets", headers=second_headers).status_code, 401)
        self.assertEqual(
            self.client.post(
                "/admin/auth/login",
                json={"username": user["username"], "password": "updated-password"},
            ).status_code,
            200,
        )

    def test_admin_password_reset_revokes_target_sessions(self) -> None:
        user, initial_password = self.create_operator()
        login = self.client.post(
            "/admin/auth/login",
            json={"username": user["username"], "password": initial_password},
        ).json()
        user_headers = {"Authorization": f"Bearer {login['access_token']}"}

        reset_response = self.client.post(
            f"/admin/users/{user['id']}/reset-password",
            headers=self.admin_headers,
            json={"new_password": "reset-password"},
        )

        self.assertEqual(reset_response.status_code, 204)
        self.assertEqual(self.client.get("/handoff-tickets", headers=user_headers).status_code, 401)

    def test_support_only_sees_and_revokes_own_sessions(self) -> None:
        support_session = self.login_support()
        support_headers = {"Authorization": f"Bearer {support_session['access_token']}"}
        support_sessions = self.client.get("/admin/sessions", headers=support_headers)
        admin_sessions = self.client.get("/admin/sessions", headers=self.admin_headers).json()
        admin_session_id = next(item["id"] for item in admin_sessions if item["username"] == self.settings.admin_username)

        forbidden_response = self.client.delete(
            f"/admin/sessions/{admin_session_id}",
            headers=support_headers,
        )

        self.assertEqual(support_sessions.status_code, 200)
        self.assertTrue(all(item["username"] == self.settings.support_username for item in support_sessions.json()))
        self.assertEqual(forbidden_response.status_code, 403)

    def test_non_local_environment_rejects_default_admin_token(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "APP_ENV": "production",
                "ADMIN_PASSWORD": "local-admin-change-me",
                "SUPPORT_PASSWORD": "local-support-change-me",
            },
        ):
            with self.assertRaisesRegex(RuntimeError, "Operations passwords"):
                create_app()


if __name__ == "__main__":
    unittest.main()
