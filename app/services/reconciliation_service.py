from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import Session

from app.models.transaction import ReconciliationStatus, Transaction


class ReconciliationService:
    """
    Matches intercompany transactions between providers (Xero, QuickBooks).

    Matching strategy: amount equality within a configurable tolerance,
    same currency, and transaction dates within a configurable window.
    """

    AMOUNT_TOLERANCE: Decimal = Decimal("0.01")
    DATE_WINDOW_DAYS: int = 3

    def find_match(
        self, transaction: Transaction, db: Session
    ) -> Optional[Transaction]:
        """
        Find a matching transaction from the opposite provider.
        Returns the best candidate or None.
        """
        candidates = (
            db.query(Transaction)
            .filter(
                Transaction.provider != transaction.provider,
                Transaction.currency == transaction.currency,
                Transaction.status == ReconciliationStatus.PENDING,
                Transaction.id != transaction.id,
            )
            .all()
        )

        for candidate in candidates:
            if self._amounts_match(transaction.amount, candidate.amount):
                if self._dates_within_window(
                    transaction.transaction_date, candidate.transaction_date
                ):
                    return candidate

        return None

    def reconcile(self, transaction: Transaction, db: Session) -> bool:
        """
        Attempt to reconcile a transaction. Returns True if a match was found.
        """
        match = self.find_match(transaction, db)
        if match is None:
            transaction.status = ReconciliationStatus.UNMATCHED
            db.commit()
            return False

        transaction.status = ReconciliationStatus.MATCHED
        transaction.matched_transaction_id = match.id
        match.status = ReconciliationStatus.MATCHED
        match.matched_transaction_id = transaction.id
        db.commit()
        return True

    def _amounts_match(self, a: Decimal, b: Decimal) -> bool:
        return abs(a - b) <= self.AMOUNT_TOLERANCE

    def _dates_within_window(self, date_a, date_b) -> bool:
        from datetime import timedelta
        delta = abs((date_a - date_b).days)
        return delta <= self.DATE_WINDOW_DAYS


reconciliation_service = ReconciliationService()
