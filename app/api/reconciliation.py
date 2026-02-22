import logging
from collections import defaultdict
from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.entity import Entity, IntercompanyTransaction
from app.models.transaction import Transaction

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reconciliation", tags=["reconciliation"])

ALLOWED_STATUSES = {"matched", "reconciled"}


# ---------------------------------------------------------------------------
# POST /detect
# ---------------------------------------------------------------------------

@router.post("/detect")
def detect_intercompany(db: Session = Depends(get_db)):
    """
    Scan all transactions across all entities, group by reference, and flag
    SPEND/RECEIVE pairs with matching amount and currency as intercompany candidates.

    Matching rules:
      - Same reference number
      - Different entities
      - One side SPEND, other side RECEIVE
      - Identical amount and currency

    Writes each new pair to intercompany_transactions with status='unmatched'.
    Idempotent: re-running skips pairs that already exist.
    """
    all_txns = (
        db.query(Transaction)
        .filter(
            Transaction.reference.isnot(None),
            Transaction.entity_id.isnot(None),
            Transaction.transaction_type.isnot(None),
        )
        .all()
    )

    by_ref: dict = defaultdict(list)
    for t in all_txns:
        by_ref[t.reference].append(t)

    pairs_created = 0
    pairs_skipped = 0
    pairs = []

    for ref, txns in by_ref.items():
        if len({t.entity_id for t in txns}) < 2:
            continue

        spends = [t for t in txns if t.transaction_type == "SPEND"]
        receives = [t for t in txns if t.transaction_type == "RECEIVE"]

        for spend in spends:
            for receive in receives:
                if spend.entity_id == receive.entity_id:
                    continue
                if spend.amount != receive.amount or spend.currency != receive.currency:
                    continue

                existing = (
                    db.query(IntercompanyTransaction)
                    .filter(
                        IntercompanyTransaction.source_transaction_id == spend.external_id,
                        IntercompanyTransaction.target_transaction_id == receive.external_id,
                    )
                    .first()
                )
                if existing:
                    pairs_skipped += 1
                    continue

                db.add(
                    IntercompanyTransaction(
                        source_entity_id=spend.entity_id,
                        target_entity_id=receive.entity_id,
                        amount=spend.amount,
                        currency=spend.currency,
                        description=spend.description or receive.description,
                        transaction_date=spend.transaction_date,
                        status="unmatched",
                        source_transaction_id=spend.external_id,
                        target_transaction_id=receive.external_id,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                )
                pairs.append(
                    {
                        "reference": ref,
                        "amount": str(spend.amount),
                        "currency": spend.currency,
                        "description": spend.description,
                        "source_transaction_id": spend.external_id,
                        "target_transaction_id": receive.external_id,
                    }
                )
                pairs_created += 1

    db.commit()
    logger.info(
        "Intercompany detection complete. pairs_created=%d pairs_skipped=%d",
        pairs_created,
        pairs_skipped,
    )
    return {"pairs_created": pairs_created, "pairs_skipped": pairs_skipped, "pairs": pairs}


# ---------------------------------------------------------------------------
# GET /pairs
# ---------------------------------------------------------------------------

def _pair_to_dict(pair: IntercompanyTransaction, db: Session) -> dict:
    """Serialize one IntercompanyTransaction with entity names and reference."""
    source_entity = db.get(Entity, pair.source_entity_id)
    target_entity = db.get(Entity, pair.target_entity_id)

    # Look up the reference from the source transaction
    source_txn = (
        db.query(Transaction)
        .filter(Transaction.external_id == pair.source_transaction_id)
        .first()
    )

    return {
        "id": str(pair.id),
        "status": pair.status,
        "reference": source_txn.reference if source_txn else None,
        "source_entity_id": str(pair.source_entity_id),
        "source_entity_name": source_entity.org_name if source_entity else None,
        "target_entity_id": str(pair.target_entity_id),
        "target_entity_name": target_entity.org_name if target_entity else None,
        "amount": str(pair.amount),
        "currency": pair.currency,
        "description": pair.description,
        "transaction_date": pair.transaction_date.isoformat() if pair.transaction_date else None,
        "source_transaction_id": pair.source_transaction_id,
        "target_transaction_id": pair.target_transaction_id,
        "created_at": pair.created_at.isoformat() if pair.created_at else None,
        "updated_at": pair.updated_at.isoformat() if pair.updated_at else None,
    }


@router.get("/pairs")
def list_pairs(
    status: str = None,
    db: Session = Depends(get_db),
):
    """
    Return all intercompany transaction pairs with entity names, amounts and status.
    Optionally filter by ?status=unmatched|matched|reconciled.
    """
    query = db.query(IntercompanyTransaction)
    if status:
        query = query.filter(IntercompanyTransaction.status == status)
    pairs = query.order_by(IntercompanyTransaction.created_at.desc()).all()
    return [_pair_to_dict(p, db) for p in pairs]


# ---------------------------------------------------------------------------
# PATCH /pairs/{id}/status
# ---------------------------------------------------------------------------

class StatusUpdate(BaseModel):
    status: Literal["matched", "reconciled"]


@router.patch("/pairs/{pair_id}/status")
def update_pair_status(
    pair_id: UUID,
    body: StatusUpdate,
    db: Session = Depends(get_db),
):
    """
    Transition an intercompany pair's status.
    Allowed transitions: unmatched → matched → reconciled.
    """
    pair = db.get(IntercompanyTransaction, pair_id)
    if not pair:
        raise HTTPException(status_code=404, detail="Pair not found")

    current = pair.status
    new = body.status

    # Enforce forward-only transitions
    order = {"unmatched": 0, "matched": 1, "reconciled": 2}
    if order.get(new, -1) <= order.get(current, -1):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot transition from '{current}' to '{new}'. Status must move forward.",
        )

    pair.status = new
    pair.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(pair)

    logger.info("Pair %s transitioned %s → %s", pair_id, current, new)
    return _pair_to_dict(pair, db)


# ---------------------------------------------------------------------------
# GET /summary
# ---------------------------------------------------------------------------

@router.get("/summary")
def reconciliation_summary(db: Session = Depends(get_db)):
    """
    Return reconciliation counts broken down by status (global) and per entity.
    Each entity row counts pairs where it appears as source OR target.
    """
    all_pairs = db.query(IntercompanyTransaction).all()
    all_entities = {e.id: e for e in db.query(Entity).all()}

    statuses = ("unmatched", "matched", "reconciled")

    # Global totals
    global_counts: dict = {s: 0 for s in statuses}
    for p in all_pairs:
        if p.status in global_counts:
            global_counts[p.status] += 1

    # Per-entity: count pairs where entity is source OR target
    entity_counts: dict = defaultdict(lambda: {s: 0 for s in statuses})
    for p in all_pairs:
        if p.status in statuses:
            entity_counts[p.source_entity_id][p.status] += 1
            entity_counts[p.target_entity_id][p.status] += 1

    by_entity = []
    for entity_id, counts in entity_counts.items():
        entity = all_entities.get(entity_id)
        by_entity.append(
            {
                "entity_id": str(entity_id),
                "entity_name": entity.org_name if entity else str(entity_id),
                "total": sum(counts.values()),
                **counts,
            }
        )
    by_entity.sort(key=lambda x: x["entity_name"])

    return {
        "total_pairs": len(all_pairs),
        "by_status": global_counts,
        "by_entity": by_entity,
    }
