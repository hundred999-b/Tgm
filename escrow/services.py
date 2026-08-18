from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from audit.models import AuditEvent
from ledger.models import LedgerAccount, LedgerEntry
from ledger.services import create_transaction

from .models import Escrow


def _escrow_accounts(escrow):
    order = escrow.order

    escrow_account = LedgerAccount.objects.select_for_update().get(
        name="ESCROW",
        currency=escrow.currency,
    )

    seller_account, _ = LedgerAccount.objects.get_or_create(
        name=f"SELLER:{order.product.seller_id}",
        currency=escrow.currency,
        defaults={
            "account_type": LedgerAccount.LIABILITY,
        },
    )

    seller_account = LedgerAccount.objects.select_for_update().get(
        pk=seller_account.pk
    )

    buyer_account = LedgerAccount.objects.select_for_update().get(
        name=f"BUYER:{order.buyer_id}",
        currency=escrow.currency,
    )

    return escrow_account, seller_account, buyer_account


@transaction.atomic
def release_escrow(escrow_id, actor=None):
    escrow = (
        Escrow.objects
        .select_for_update()
        .select_related(
            "order",
            "order__buyer",
            "order__product",
            "order__product__seller",
        )
        .get(pk=escrow_id)
    )

    if escrow.status != Escrow.HOLDING:
        raise ValueError(
            f"Escrow is not releasable. Current status: {escrow.status}"
        )

    amount = Decimal(str(escrow.amount))

    escrow_account, seller_account, _ = _escrow_accounts(escrow)

    tx = create_transaction(
        description=f"Release escrow #{escrow.pk}",
        reference=f"ESCROW_RELEASE:{escrow.pk}",
        postings=[
            {
                "account": escrow_account,
                "direction": LedgerEntry.DEBIT,
                "amount": amount,
            },
            {
                "account": seller_account,
                "direction": LedgerEntry.CREDIT,
                "amount": amount,
            },
        ],
        metadata={
            "escrow_id": escrow.pk,
            "order_id": escrow.order_id,
            "operation": "release",
        },
    )

    escrow.status = Escrow.RELEASED
    escrow.released_at = timezone.now()
    escrow.save(
        update_fields=["status", "released_at"]
    )

    escrow.order.status = escrow.order.COMPLETED
    escrow.order.save(update_fields=["status"])

    AuditEvent.objects.create(
        actor=actor,
        action="escrow.released",
        object_type="Escrow",
        object_id=str(escrow.pk),
        metadata={
            "order_id": escrow.order_id,
            "amount": str(amount),
            "currency": escrow.currency,
            "transaction_id": tx.transaction_id,
        },
    )

    return tx


@transaction.atomic
def refund_escrow(escrow_id, actor=None):
    escrow = (
        Escrow.objects
        .select_for_update()
        .select_related(
            "order",
            "order__buyer",
        )
        .get(pk=escrow_id)
    )

    if escrow.status != Escrow.HOLDING:
        raise ValueError(
            f"Escrow is not refundable. Current status: {escrow.status}"
        )

    amount = Decimal(str(escrow.amount))

    escrow_account, _, buyer_account = _escrow_accounts(escrow)

    tx = create_transaction(
        description=f"Refund escrow #{escrow.pk}",
        reference=f"ESCROW_REFUND:{escrow.pk}",
        postings=[
            {
                "account": escrow_account,
                "direction": LedgerEntry.DEBIT,
                "amount": amount,
            },
            {
                "account": buyer_account,
                "direction": LedgerEntry.CREDIT,
                "amount": amount,
            },
        ],
        metadata={
            "escrow_id": escrow.pk,
            "order_id": escrow.order_id,
            "operation": "refund",
        },
    )

    escrow.status = Escrow.REFUNDED
    escrow.save(update_fields=["status"])

    escrow.order.status = escrow.order.REFUNDED
    escrow.order.save(update_fields=["status"])

    AuditEvent.objects.create(
        actor=actor,
        action="escrow.refunded",
        object_type="Escrow",
        object_id=str(escrow.pk),
        metadata={
            "order_id": escrow.order_id,
            "amount": str(amount),
            "currency": escrow.currency,
            "transaction_id": tx.transaction_id,
        },
    )

    return tx
