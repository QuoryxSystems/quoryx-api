from datetime import datetime
import uuid
import enum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Numeric, String, Uuid
from sqlalchemy.orm import relationship

from app.models.database import Base


class IntercompanyStatus(str, enum.Enum):
    UNMATCHED = "unmatched"
    MATCHED = "matched"
    RECONCILED = "reconciled"


class Entity(Base):
    __tablename__ = "entities"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False, unique=True)
    org_name = Column(String(255), nullable=False)
    currency = Column(String(3), nullable=False)
    country_code = Column(String(3), nullable=True)
    connected_at = Column(DateTime, default=datetime.utcnow)

    source_transactions = relationship(
        "IntercompanyTransaction",
        foreign_keys="IntercompanyTransaction.source_entity_id",
        back_populates="source_entity",
    )
    target_transactions = relationship(
        "IntercompanyTransaction",
        foreign_keys="IntercompanyTransaction.target_entity_id",
        back_populates="target_entity",
    )


class IntercompanyTransaction(Base):
    __tablename__ = "intercompany_transactions"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_entity_id = Column(
        Uuid(as_uuid=True), ForeignKey("entities.id"), nullable=False
    )
    target_entity_id = Column(
        Uuid(as_uuid=True), ForeignKey("entities.id"), nullable=True
    )
    amount = Column(Numeric(18, 2), nullable=False)
    currency = Column(String(3), nullable=False)
    description = Column(String(500), nullable=True)
    transaction_date = Column(DateTime, nullable=False)
    status = Column(
        Enum(IntercompanyStatus),
        nullable=False,
        default=IntercompanyStatus.UNMATCHED,
    )
    source_transaction_id = Column(String(255), nullable=True)
    target_transaction_id = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    source_entity = relationship(
        "Entity",
        foreign_keys=[source_entity_id],
        back_populates="source_transactions",
    )
    target_entity = relationship(
        "Entity",
        foreign_keys=[target_entity_id],
        back_populates="target_transactions",
    )
