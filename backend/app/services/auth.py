"""Optional local accounts: salted scrypt, hashed opaque sessions, CSRF and throttling."""

import hashlib
import hmac
import secrets
from datetime import UTC, timedelta

from fastapi import Request, Response
from sqlalchemy import case, delete, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.errors import AppError
from app.db.base import utcnow
from app.db.models import AuthAttemptRow, AuthSessionRow, UserRow
from app.schemas.auth import AuthState, Credentials, User

COOKIE = "realty_session"
CSRF_COOKIE = "realty_csrf"


class Unauthorized(AppError):
    status_code = 401
    code = "unauthorized"


class Forbidden(AppError):
    status_code = 403
    code = "forbidden"


class AuthRateLimited(AppError):
    status_code = 429
    code = "auth_rate_limited"


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _derive(password: str, salt: bytes) -> str:
    # OWASP scrypt minimum: N=2^17, r=8, p=1, 128 MiB plus overhead.
    return hashlib.scrypt(
        password.encode(), salt=salt, n=2**17, r=8, p=1, maxmem=256 * 1024 * 1024, dklen=64
    ).hex()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    return salt.hex() + ":" + _derive(password, salt)


def verify_password(password: str, encoded: str | None) -> bool:
    salt, expected = encoded.split(":") if encoded else ("00" * 16, "00" * 64)
    return (
        hmac.compare_digest(_derive(password, bytes.fromhex(salt)), expected)
        and encoded is not None
    )


def check_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    allowed = {*get_settings().cors_origins, str(request.base_url).rstrip("/")}
    if origin and origin.rstrip("/") not in allowed:
        raise Forbidden("Request origin is not allowed")


def _enabled() -> None:
    if not get_settings().auth_enabled:
        raise Forbidden("Accounts are disabled in local demo mode")


def _throttle(db: Session, request: Request) -> None:
    now = utcnow()
    window = int(now.timestamp()) // 900
    key = _digest(request.client.host if request.client else "unknown")
    db.execute(delete(AuthAttemptRow).where(AuthAttemptRow.window < window - 96))
    stmt = insert(AuthAttemptRow).values(key=key, window=window, attempts=1)
    stmt = stmt.on_conflict_do_update(
        index_elements=["key"],
        set_={
            "window": window,
            "attempts": case(
                (AuthAttemptRow.window == window, AuthAttemptRow.attempts + 1), else_=1
            ),
        },
    ).returning(AuthAttemptRow.attempts)
    attempts = db.scalar(stmt)
    db.commit()
    if attempts > 10:
        raise AuthRateLimited("Too many account attempts. Try again in 15 minutes.")


def current_session(db: Session, request: Request) -> AuthSessionRow | None:
    token = request.cookies.get(COOKIE, "")
    row = db.get(AuthSessionRow, _digest(token)) if token and len(token) <= 128 else None
    if row and row.expires_at.replace(tzinfo=row.expires_at.tzinfo or UTC) > utcnow():
        return row
    return None


def state(db: Session, request: Request) -> AuthState:
    if not get_settings().auth_enabled:
        return AuthState(enabled=False)
    row = current_session(db, request)
    user = db.get(UserRow, row.user_id) if row else None
    return AuthState(enabled=True, user=User(id=user.id, username=user.username) if user else None)


def require_session(db: Session, request: Request) -> None:
    if not get_settings().auth_enabled:
        db.info["owner_id"] = "local"
        return
    row = current_session(db, request)
    if row is None:
        raise Unauthorized("Sign in to access your account")
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        check_origin(request)
        token = request.headers.get("X-CSRF-Token", "")
        if not token or not hmac.compare_digest(_digest(token), row.csrf_hash):
            raise Forbidden("CSRF token missing or invalid; refresh and retry")
    db.info["owner_id"] = row.user_id


def _login_session(db: Session, user: UserRow, request: Request, response: Response) -> AuthState:
    settings = get_settings()
    old = current_session(db, request)
    if old:
        db.delete(old)
    db.execute(
        delete(AuthSessionRow)
        .where(AuthSessionRow.expires_at < utcnow())
        .execution_options(synchronize_session=False)
    )
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    db.add(
        AuthSessionRow(
            token_hash=_digest(token),
            user_id=user.id,
            csrf_hash=_digest(csrf),
            expires_at=utcnow() + timedelta(hours=settings.auth_session_hours),
        )
    )
    db.commit()
    for key, value, http_only in ((COOKIE, token, True), (CSRF_COOKIE, csrf, False)):
        response.set_cookie(
            key,
            value,
            httponly=http_only,
            secure=settings.auth_cookie_secure,
            samesite="strict",
            max_age=settings.auth_session_hours * 3600,
            path="/",
        )
    response.headers["Cache-Control"] = "no-store"
    return AuthState(enabled=True, user=User(id=user.id, username=user.username))


def register(
    db: Session, credentials: Credentials, request: Request, response: Response
) -> AuthState:
    _enabled()
    check_origin(request)
    _throttle(db, request)
    row = UserRow(
        username=credentials.username,
        password_hash=hash_password(credentials.password.get_secret_value()),
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise Forbidden("Unable to register these credentials; choose another username") from exc
    return _login_session(db, row, request, response)


def login(db: Session, credentials: Credentials, request: Request, response: Response) -> AuthState:
    _enabled()
    check_origin(request)
    _throttle(db, request)
    user = db.scalar(select(UserRow).where(UserRow.username == credentials.username))
    if not verify_password(
        credentials.password.get_secret_value(), user.password_hash if user else None
    ):
        raise Unauthorized("Invalid username or password")
    return _login_session(db, user, request, response)


def logout(db: Session, request: Request, response: Response) -> AuthState:
    require_session(db, request)
    row = current_session(db, request)
    if row:
        db.delete(row)
        db.commit()
    response.delete_cookie(COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")
    response.headers["Cache-Control"] = "no-store"
    return AuthState(enabled=get_settings().auth_enabled)
