import sys
from pathlib import Path

ROOT = Path.cwd()


def put(name, text):
    p = ROOT / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text.strip() + "\n", encoding="utf-8")
    print("[+] " + name)


# ============================================================
# TRANSACTION SERVICE
# ============================================================

put("ledger/transaction_service.py", r'''
from decimal import Decimal
from uuid import uuid4

from django.db import transaction

from .models import LedgerAccount, LedgerEntry
from .services import create_transaction, account_balance


@transaction.atomic
def test_deposit(user, amount, currency="USD"):
    """
    Local/test deposit.

    This is NOT a real payment.
    It simply creates accounting entries for development.
    """

    amount = Decimal(str(amount))

    if amount <= 0:
        raise ValueError("Deposit must be greater than zero")

    buyer_account = LedgerAccount.objects.select_for_update().get(
        name=f"BUYER:{user.id}",
        currency=currency,
    )

    clearing = LedgerAccount.objects.select_for_update().get(
        name="PAYMENT_CLEARING",
        currency=currency,
    )

    tx = create_transaction(
        description=f"Test deposit for {user.username}",
        reference=f"TEST_DEPOSIT:{uuid4().hex}",
        postings=[
            {
                "account": clearing,
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
            "test": True,
            "user_id": user.id,
        },
    )

    return tx


def wallet_balance(user, currency="USD"):
    account = LedgerAccount.objects.get(
        name=f"BUYER:{user.id}",
        currency=currency,
    )

    return account_balance(account)


@transaction.atomic
def purchase_order(order):
    """
    Move buyer funds into escrow.

    This does not create the order; it funds an existing order.
    """

    from escrow.models import Escrow

    if order.status != "pending":
        raise ValueError(
            f"Order cannot be purchased from status {order.status}"
        )

    amount = Decimal(str(order.amount))

    buyer_account = LedgerAccount.objects.select_for_update().get(
        name=f"BUYER:{order.buyer_id}",
        currency=order.currency,
    )

    escrow_account = LedgerAccount.objects.select_for_update().get(
        name="ESCROW",
        currency=order.currency,
    )

    balance = account_balance(buyer_account)

    if balance < amount:
        raise ValueError(
            f"Insufficient funds: balance={balance}, required={amount}"
        )

    tx = create_transaction(
        description=f"Fund order #{order.id}",
        reference=f"ORDER_ESCROW:{order.id}",
        postings=[
            {
                "account": buyer_account,
                "direction": LedgerEntry.DEBIT,
                "amount": amount,
            },
            {
                "account": escrow_account,
                "direction": LedgerEntry.CREDIT,
                "amount": amount,
            },
        ],
        metadata={
            "order_id": order.id,
            "buyer_id": order.buyer_id,
        },
    )

    Escrow.objects.create(
        order=order,
        amount=amount,
        currency=order.currency,
        status=Escrow.HOLDING,
    )

    order.status = order.ESCROW
    order.save(update_fields=["status"])

    return tx
''')


# ============================================================
# TEST MANAGEMENT COMMAND
# ============================================================

put("marketplace/management/__init__.py", "")

put("marketplace/management/commands/__init__.py", "")

put("marketplace/management/commands/test_marketplace.py", r'''
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
''')


# ============================================================
# API
# ============================================================

put("marketplace/api.py", r'''
from django.contrib.auth.models import User
from django.http import JsonResponse

from ledger.transaction_service import (
    test_deposit,
    wallet_balance,
)


def wallet(request):

    if not request.user.is_authenticated:
        return JsonResponse(
            {"error": "authentication required"},
            status=401,
        )

    balance = wallet_balance(request.user)

    return JsonResponse({
        "user": request.user.username,
        "currency": "USD",
        "balance": str(balance),
    })


def test_deposit_api(request):

    if request.method != "POST":
        return JsonResponse(
            {"error": "POST required"},
            status=405,
        )

    if not request.user.is_authenticated:
        return JsonResponse(
            {"error": "authentication required"},
            status=401,
        )

    tx = test_deposit(
        request.user,
        "100.00",
        "USD",
    )

    return JsonResponse({
        "test": True,
        "transaction_id": tx.transaction_id,
        "balance": str(
            wallet_balance(request.user)
        ),
    })
''')


# ============================================================
# URLS
# ============================================================

urls = ROOT / "config/urls.py"
u = urls.read_text()

if "wallet" not in u:
    u = u.replace(
        "from django.urls import path",
        "from django.urls import path\nfrom marketplace.api import wallet, test_deposit_api",
    )

    u = u.replace(
        "urlpatterns = [",
        """urlpatterns = [
    path("api/wallet/", wallet),
    path("api/test-deposit/", test_deposit_api),
"""
    )

    urls.write_text(u, encoding="utf-8")


# ============================================================
# RUN CHECK
# ============================================================

import subprocess

subprocess.check_call(
    [sys.executable, "manage.py", "check"],
    cwd=ROOT,
)

print()
print("=" * 60)
print("TRANSACTION ENGINE READY")
print("=" * 60)
print()
print("Run the local test with:")
print()
print("python3 manage.py test_marketplace")
print()
