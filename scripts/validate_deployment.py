#!/usr/bin/env python3
"""Validate public frontend, backend health and browser CORS configuration."""

import argparse
import json
import sys
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, ProxyHandler


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a deployed Football Gear AI Assistant instance.")
    parser.add_argument("--backend", required=True, help="Public backend URL, for example https://api.example.com")
    parser.add_argument("--frontend", required=True, help="Public frontend URL, for example https://app.example.com")
    return parser.parse_args()


def request(url: str, method: str = "GET", headers: Optional[dict[str, str]] = None):
    opener = build_opener(ProxyHandler({}))
    return opener.open(Request(url, method=method, headers=headers or {}), timeout=20)


def validate(backend_url: str, frontend_url: str) -> None:
    backend_url = backend_url.rstrip("/")
    frontend_url = frontend_url.rstrip("/")

    with request(f"{backend_url}/health") as response:
        health = json.load(response)
    if response.status != 200 or health.get("status") != "ok" or health.get("products", 0) < 1:
        raise RuntimeError(f"Backend health check failed: {health}")
    print(f"PASS backend health: {health['products']} products, {health['faq_articles']} FAQs")

    with request(
        f"{backend_url}/chat",
        method="OPTIONS",
        headers={
            "Origin": frontend_url,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    ) as response:
        allowed_origin = response.headers.get("Access-Control-Allow-Origin")
    if allowed_origin != frontend_url:
        raise RuntimeError(
            f"CORS check failed: expected {frontend_url}, received {allowed_origin or 'no origin header'}"
        )
    print(f"PASS backend CORS: {allowed_origin}")

    with request(frontend_url) as response:
        content_type = response.headers.get("Content-Type", "")
    if response.status != 200 or "text/html" not in content_type:
        raise RuntimeError(f"Frontend check failed: HTTP {response.status}, {content_type}")
    print("PASS frontend: HTML page is reachable")


def main() -> int:
    args = parse_args()
    try:
        validate(args.backend, args.frontend)
    except (HTTPError, URLError, RuntimeError, TimeoutError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
