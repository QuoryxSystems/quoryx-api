import hashlib
import hmac
import secrets
from app.core.config import settings


def generate_state_token() -> str:
    """Generate a cryptographically secure state token for OAuth flows."""
    return secrets.token_urlsafe(32)


def verify_state_token(token: str, expected: str) -> bool:
    """Constant-time comparison to verify OAuth state tokens."""
    return hmac.compare_digest(token.encode(), expected.encode())


def hash_token(token: str) -> str:
    """One-way hash a token for safe storage."""
    return hashlib.sha256(
        (token + settings.APP_SECRET_KEY).encode()
    ).hexdigest()
