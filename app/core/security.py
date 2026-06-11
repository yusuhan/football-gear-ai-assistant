"""Password, session-token and authorization helpers for operations APIs."""

import hashlib
import secrets
from dataclasses import dataclass
from hmac import compare_digest
from typing import Optional

from fastapi import Depends, Header, HTTPException, Request, status

PASSWORD_ITERATIONS = 210_000


@dataclass(frozen=True)
class Operator:
    """Authenticated operations user attached to a request."""

    id: str
    username: str
    role: str
    session_id: str


def hash_password(password: str, salt: Optional[str] = None) -> str:
    """Hash a password using PBKDF2 from the Python standard library."""

    password_salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(password_salt),
        PASSWORD_ITERATIONS,
    ).hex()
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${password_salt}${digest}"


def verify_password(password: str, encoded_password: str) -> bool:
    """Verify a password against a stored PBKDF2 hash."""

    try:
        algorithm, iterations, salt, expected_digest = encoded_password.split("$", 3)
        iteration_count = int(iterations)
    except (TypeError, ValueError):
        return False
    if algorithm != "pbkdf2_sha256" or iteration_count != PASSWORD_ITERATIONS:
        return False
    actual_digest = hash_password(password, salt).rsplit("$", 1)[-1]
    return compare_digest(actual_digest, expected_digest)


def create_session_token() -> str:
    """Create an opaque token returned once to the authenticated client."""

    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    """Hash a session token before persistence."""

    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def require_operator(
    request: Request,
    authorization: Optional[str] = Header(default=None),
) -> Operator:
    """Resolve a valid operations session from a Bearer token."""

    scheme, _, token = (authorization or "").partition(" ")
    operator = None
    if scheme.lower() == "bearer" and token:
        operator = request.app.state.operations_repository.get_operator_by_session(token)
    if not operator:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid admin credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Operator(**operator)


def require_admin(operator: Operator = Depends(require_operator)) -> Operator:
    """Allow only administrators to access a protected endpoint."""

    if operator.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin role required")
    return operator
