import sys
from pathlib import Path

ROOT = Path.cwd()


def put(name, text):
    p = ROOT / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text.strip() + "\n", encoding="utf-8")
    print("[+] " + name)


# ============================================================
# ESCROW SERVICE — RELEASE + REFUND
# ============================================================

put("escrow/services.py", r'''
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

    seller_account = LedgerAccount.objects.select_for_update().get(
        name=f"SELLER:{order.product.seller_id}",
        currency=escrow.currency,
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
''')


# ============================================================
# ESCROW ADMIN ACTIONS
# ============================================================

put("escrow/admin.py", r'''
from django.contrib import admin, messages

from .models import Escrow
from .services import release_escrow, refund_escrow


@admin.register(Escrow)
class EscrowAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "order",
        "amount",
        "currency",
        "status",
        "created_at",
        "released_at",
    )

    list_filter = (
        "status",
        "currency",
    )

    search_fields = (
        "order__id",
        "order__buyer__username",
        "order__product__title",
    )

    actions = [
        "release_selected",
        "refund_selected",
    ]

    @admin.action(description="Release selected escrow")
    def release_selected(self, request, queryset):

        success = 0

        for escrow in queryset:

            try:
                release_escrow(
                    escrow.pk,
                    actor=request.user,
                )

                success += 1

            except Exception as exc:

                self.message_user(
                    request,
                    f"Escrow #{escrow.pk}: {exc}",
                    level=messages.ERROR,
                )

        if success:
            self.message_user(
                request,
                f"{success} escrow(s) released.",
                level=messages.SUCCESS,
            )

    @admin.action(description="Refund selected escrow")
    def refund_selected(self, request, queryset):

        success = 0

        for escrow in queryset:

            try:
                refund_escrow(
                    escrow.pk,
                    actor=request.user,
                )

                success += 1

            except Exception as exc:

                self.message_user(
                    request,
                    f"Escrow #{escrow.pk}: {exc}",
                    level=messages.ERROR,
                )

        if success:
            self.message_user(
                request,
                f"{success} escrow(s) refunded.",
                level=messages.SUCCESS,
            )
''')


# ============================================================
# TEST COMMAND
# ============================================================

put("escrow/management/__init__.py", "")

put("escrow/management/commands/__init__.py", "")

put("escrow/management/commands/test_escrow.py", r'''
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from escrow.models import Escrow
from escrow.services import release_escrow, refund_escrow
from ledger.transaction_service import (
    test_deposit,
    wallet_balance,
)
from marketplace.models import Product, Order


class Command(BaseCommand):
    help = "Test escrow release and refund"


    def handle(self, *args, **options):

        buyer = User.objects.filter(
            username="snoobdevma"
        ).first()

        if not buyer:
            raise RuntimeError("snoobdevma user not found")

        seller = User.objects.filter(
            username="test_seller"
        ).first()

        if not seller:
            seller = User.objects.create_user(
                username="test_seller",
                password="local-test-only",
            )

        # ====================================================
        # RELEASE TEST
        # ====================================================

        self.stdout.write("")
        self.stdout.write("=== RELEASE TEST ===")

        test_deposit(
            buyer,
            Decimal("50.00"),
            "USD",
        )

        product = Product.objects.create(
            seller=seller,
            title="Release Test Product",
            description="Local escrow release test",
            price=Decimal("20.00"),
            currency="USD",
            active=True,
        )

        order = Order.objects.create(
            buyer=buyer,
            product=product,
            amount=product.price,
            currency=product.currency,
            status=Order.PENDING,
        )

        from ledger.transaction_service import purchase_order

        purchase_order(order)

        escrow = Escrow.objects.get(
            order=order
        )

        buyer_before = wallet_balance(buyer)

        tx = release_escrow(
            escrow.pk,
            actor=buyer,
        )

        escrow.refresh_from_db()
        order.refresh_from_db()

        self.stdout.write(
            f"Release transaction: {tx.transaction_id}"
        )

        self.stdout.write(
            f"Escrow status: {escrow.status}"
        )

        self.stdout.write(
            f"Order status: {order.status}"
        )

        self.stdout.write(
            f"Buyer balance: {wallet_balance(buyer)} USD"
        )

        assert escrow.status == Escrow.RELEASED
        assert order.status == Order.COMPLETED
        assert wallet_balance(buyer) == buyer_before

        self.stdout.write(
            self.style.SUCCESS(
                "RELEASE TEST PASSED"
            )
        )

        # ====================================================
        # REFUND TEST
        # ====================================================

        self.stdout.write("")
        self.stdout.write("=== REFUND TEST ===")

        test_deposit(
            buyer,
            Decimal("50.00"),
            "USD",
        )

        product2 = Product.objects.create(
            seller=seller,
            title="Refund Test Product",
            description="Local escrow refund test",
            price=Decimal("15.00"),
            currency="USD",
            active=True,
        )

        order2 = Order.objects.create(
            buyer=buyer,
            product=product2,
            amount=product2.price,
            currency=product2.currency,
            status=Order.PENDING,
        )

        purchase_order(order2)

        escrow2 = Escrow.objects.get(
            order=order2
        )

        balance_before_refund = wallet_balance(buyer)

        tx2 = refund_escrow(
            escrow2.pk,
            actor=buyer,
        )

        escrow2.refresh_from_db()
        order2.refresh_from_db()

        self.stdout.write(
            f"Refund transaction: {tx2.transaction_id}"
        )

        self.stdout.write(
            f"Escrow status: {escrow2.status}"
        )

        self.stdout.write(
            f"Order status: {order2.status}"
        )

        self.stdout.write(
            f"Buyer balance: {wallet_balance(buyer)} USD"
        )

        assert escrow2.status == Escrow.REFUNDED
        assert order2.status == Order.REFUNDED
        assert wallet_balance(buyer) == balance_before_refund + Decimal("15.00")

        self.stdout.write(
            self.style.SUCCESS(
                "REFUND TEST PASSED"
            )
        )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "ALL ESCROW TESTS PASSED"
            )
        )
''')


# ============================================================
# CHECK
# ============================================================

import subprocess

subprocess.check_call(
    [sys.executable, "manage.py", "check"],
    cwd=ROOT,
)

print()
print("=" * 60)
print("ESCROW LIFECYCLE READY")
print("=" * 60)
print()
print("Test:")
print("python3 manage.py test_escrow")
