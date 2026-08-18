from decimal import Decimal

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from ledger.transaction_service import (
    test_deposit,
    wallet_balance,
    purchase_order,
)

from marketplace.models import Product, Order


class Command(BaseCommand):
    help = "Run a complete local marketplace test"


    def handle(self, *args, **options):

        user = User.objects.filter(
            username="snoobdevma"
        ).first()

        if not user:
            user = User.objects.first()

        if not user:
            self.stderr.write(
                "No user exists. Create a superuser first."
            )
            return

        self.stdout.write(
            f"Using user: {user.username}"
        )

        # ----------------------------------------------------
        # Deposit test funds
        # ----------------------------------------------------

        before = wallet_balance(user)

        self.stdout.write(
            f"Balance before deposit: {before} USD"
        )

        deposit = test_deposit(
            user,
            Decimal("100.00"),
            "USD",
        )

        after = wallet_balance(user)

        self.stdout.write(
            self.style.SUCCESS(
                f"Deposit created: {deposit.transaction_id}"
            )
        )

        self.stdout.write(
            f"Balance after deposit: {after} USD"
        )

        # ----------------------------------------------------
        # Create seller
        # ----------------------------------------------------

        seller = User.objects.filter(
            username="test_seller"
        ).first()

        if not seller:
            seller = User.objects.create_user(
                username="test_seller",
                password="local-test-only",
            )

        # ----------------------------------------------------
        # Create product
        # ----------------------------------------------------

        product = Product.objects.create(
            seller=seller,
            title="Local Test Product",
            description="Development marketplace product",
            price=Decimal("25.00"),
            currency="USD",
            active=True,
        )

        self.stdout.write(
            f"Product created: #{product.id}"
        )

        # ----------------------------------------------------
        # Create order
        # ----------------------------------------------------

        order = Order.objects.create(
            buyer=user,
            product=product,
            amount=product.price,
            currency=product.currency,
            status=Order.PENDING,
        )

        self.stdout.write(
            f"Order created: #{order.id}"
        )

        # ----------------------------------------------------
        # Fund escrow
        # ----------------------------------------------------

        tx = purchase_order(order)

        self.stdout.write(
            self.style.SUCCESS(
                f"Escrow funded: {tx.transaction_id}"
            )
        )

        self.stdout.write(
            f"Order status: {order.status}"
        )

        self.stdout.write(
            f"Buyer balance: {wallet_balance(user)} USD"
        )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "LOCAL MARKETPLACE TEST PASSED"
            )
        )
