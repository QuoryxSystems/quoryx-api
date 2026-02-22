import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.transaction import OAuthToken
from app.services.oauth_service import oauth_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

# In production, store state tokens server-side (e.g. Redis) keyed to a session.
# This in-memory dict is sufficient for single-process development only.
_pending_states: dict[str, dict] = {}


@router.get("/xero/login")
def xero_login(entity_name: Optional[str] = Query(None)):
    """
    Redirect the user to Xero's authorization page to begin OAuth 2.0.
    Pass entity_name to label which organisation is connecting (informational only).
    """
    url, state = oauth_service.get_xero_authorization_url()
    _pending_states[state] = {"provider": "xero", "entity_name": entity_name}
    logger.info("Initiating Xero OAuth flow. entity_name=%s", entity_name)
    return RedirectResponse(url=url)


@router.get("/xero/callback")
async def xero_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
):
    """
    Handle the Xero OAuth callback:
    - Validate state token
    - Exchange authorization code for access + refresh tokens
    - Upsert the token keyed on tenant_id (supports multiple entities)
    - Auto-sync the connected entity into the entities table
    """
    state_data = _pending_states.pop(state, None)
    if not state_data or state_data.get("provider") != "xero":
        raise HTTPException(status_code=400, detail="Invalid or expired state token")

    try:
        token_data = await oauth_service.exchange_xero_code(code)
    except Exception as exc:
        logger.error("Xero token exchange failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"Xero OAuth failed: {exc}")

    tenant_id = token_data["tenant_id"]

    # Upsert keyed on tenant_id + provider so each Xero org gets its own row
    existing = (
        db.query(OAuthToken)
        .filter(OAuthToken.tenant_id == tenant_id, OAuthToken.provider == "xero")
        .first()
    )
    if existing:
        existing.access_token = token_data["access_token"]
        existing.refresh_token = token_data["refresh_token"]
        existing.expires_at = token_data["expires_at"]
        db.commit()
        db.refresh(existing)
        token = existing
    else:
        token = OAuthToken(
            user_id=tenant_id,  # tenant_id as user_id gives a unique, meaningful value
            provider="xero",
            access_token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            expires_at=token_data["expires_at"],
            tenant_id=tenant_id,
        )
        db.add(token)
        db.commit()
        db.refresh(token)

    logger.info(
        "Xero OAuth connected. token_id=%s tenant_id=%s entity_name=%s",
        token.id,
        tenant_id,
        state_data.get("entity_name"),
    )

    # Auto-sync the entity — import here to avoid circular dependency
    from app.api.entities import sync_entity_from_token  # noqa: PLC0415

    try:
        entity_result = await sync_entity_from_token(token, db)
    except Exception as exc:
        logger.warning("Entity auto-sync failed after OAuth (token saved): %s", exc)
        entity_result = None

    return {
        "status": "connected",
        "provider": "xero",
        "token_id": str(token.id),
        "tenant_id": token.tenant_id,
        "entity": entity_result,
    }


@router.get("/quickbooks/login")
def quickbooks_login():
    """Redirect the user to QuickBooks' authorization page to begin OAuth 2.0."""
    url, state = oauth_service.get_quickbooks_authorization_url()
    _pending_states[state] = {"provider": "quickbooks"}
    logger.info("Initiating QuickBooks OAuth flow, redirecting to authorization URL")
    return RedirectResponse(url=url)


@router.get("/quickbooks/callback")
async def quickbooks_callback(
    code: str = Query(...),
    state: str = Query(...),
    realmId: str = Query(...),
    db: Session = Depends(get_db),
):
    """Handle the QuickBooks OAuth callback and store tokens."""
    state_data = _pending_states.pop(state, None)
    if not state_data or state_data.get("provider") != "quickbooks":
        raise HTTPException(status_code=400, detail="Invalid or expired state token")

    try:
        token_data = await oauth_service.exchange_quickbooks_code(code, realmId)
    except Exception as exc:
        logger.error("QuickBooks token exchange failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"QuickBooks OAuth failed: {exc}")

    existing = (
        db.query(OAuthToken)
        .filter(
            OAuthToken.user_id == "default_user",
            OAuthToken.provider == "quickbooks",
        )
        .first()
    )
    if existing:
        existing.access_token = token_data["access_token"]
        existing.refresh_token = token_data["refresh_token"]
        existing.expires_at = token_data["expires_at"]
        existing.tenant_id = token_data.get("realm_id")
        db.commit()
        db.refresh(existing)
        token = existing
    else:
        token = OAuthToken(
            user_id="default_user",
            provider="quickbooks",
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token"),
            expires_at=token_data["expires_at"],
            tenant_id=token_data.get("realm_id"),
        )
        db.add(token)
        db.commit()
        db.refresh(token)

    logger.info("QuickBooks OAuth connected successfully. token_id=%s", token.id)
    return {
        "status": "connected",
        "provider": "quickbooks",
        "token_id": str(token.id),
    }
