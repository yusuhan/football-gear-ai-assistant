"""Dependency-free smoke test for a running local or Compose stack."""

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from typing import Optional


API_BASE_URL = os.getenv("SMOKE_API_BASE_URL", "http://127.0.0.1:8000")
FRONTEND_URL = os.getenv("SMOKE_FRONTEND_URL", "http://127.0.0.1:3000")
LOCAL_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def request(
    path: str,
    method: str = "GET",
    payload: Optional[dict] = None,
    token: Optional[str] = None,
):
    headers = {}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = LOCAL_OPENER.open(
        urllib.request.Request(API_BASE_URL + path, data=data, headers=headers, method=method),
        timeout=5,
    )
    body = response.read()
    return response.status, json.loads(body) if body else None


def wait_for_services(timeout: int = 90) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            LOCAL_OPENER.open(API_BASE_URL + "/health", timeout=2)
            LOCAL_OPENER.open(FRONTEND_URL, timeout=2)
            return
        except (OSError, urllib.error.URLError):
            time.sleep(1)
    raise RuntimeError("services did not become ready before timeout")


def run() -> None:
    health_status, health = request("/health")
    assert health_status == 200 and health["status"] == "ok"

    chat_status, chat = request("/chat", "POST", {"message": "Mercurial 16 Elite有43码吗"})
    assert chat_status == 200 and chat["route"] == "tool"

    login_status, login = request(
        "/admin/auth/login",
        "POST",
        {
            "username": os.getenv("ADMIN_USERNAME", "admin"),
            "password": os.getenv("ADMIN_PASSWORD", "local-admin-change-me"),
        },
    )
    assert login_status == 200 and login["operator"]["role"] == "admin"

    users_status, users = request("/admin/users", token=login["access_token"])
    assert users_status == 200 and len(users) >= 2
    print("Smoke test passed: frontend, health, chat, login and operations APIs are ready.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--wait", action="store_true", help="wait for services before testing")
    args = parser.parse_args()
    if args.wait:
        wait_for_services()
    run()
