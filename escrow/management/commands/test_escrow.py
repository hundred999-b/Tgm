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
