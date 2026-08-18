import sys
from pathlib import Path

ROOT = Path.cwd()


def put(name, text):
    p = ROOT / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text.strip() + "\n", encoding="utf-8")
    print("[+] " + name)


# ============================================================
# WALLET
# ============================================================

put("ledger/services.py", r'''
from decimal import Decimal
from uuid import uuid4

from django.db import transaction
from django.db.models import Sum

from .models import LedgerAccount, LedgerEntry, LedgerTransaction


ZERO = Decimal("0")


@transaction.atomic
def create_transaction(
    description,
    postings,
    reference="",
    metadata=None,
):
    """
    postings:
        [
            {
                "account": LedgerAccount,
                "direction": "debit" or "credit",
                "amount": Decimal(...)
            },
            ...
        ]

    A transaction must balance:
        total debits == total credits
    """

    if not postings:
        raise ValueError("A transaction needs postings")

    debit = sum(
        (Decimal(str(x["amount"])) for x in postings
         if x["direction"] == LedgerEntry.DEBIT),
        ZERO,
    )

    credit = sum(
        (Decimal(str(x["amount"])) for x in postings
         if x["direction"] == LedgerEntry.CREDIT),
        ZERO,
    )

    if debit <= ZERO:
        raise ValueError("Transaction amount must be positive")

    if debit != credit:
        raise ValueError(
            f"Unbalanced transaction: debit={debit}, credit={credit}"
        )

    currencies = {
        x["account"].currency
        for x in postings
    }

    if len(currencies) != 1:
        raise ValueError(
            "All postings in a transaction must use one currency"
        )

    tx = LedgerTransaction.objects.create(
        transaction_id=uuid4().hex,
        description=description,
        reference=reference,
        metadata=metadata or {},
    )

    LedgerEntry.objects.bulk_create([
        LedgerEntry(
            transaction=tx,
            account=x["account"],
            amount=Decimal(str(x["amount"])),
            direction=x["direction"],
        )
        for x in postings
    ])

    return tx


def account_balance(account):
    """
    Returns the signed balance of an account.

    Asset/expense:
        debit increases balance

    Liability/revenue/equity:
        credit increases balance
    """

    debit = LedgerEntry.objects.filter(
        account=account,
        direction=LedgerEntry.DEBIT,
    ).aggregate(
        total=Sum("amount")
    )["total"] or ZERO

    credit = LedgerEntry.objects.filter(
        account=account,
        direction=LedgerEntry.CREDIT,
    ).aggregate(
        total=Sum("amount")
    )["total"] or ZERO

    if account.account_type in (
        LedgerAccount.ASSET,
        LedgerAccount.EXPENSE,
    ):
        return debit - credit

    return credit - debit
''')


# ============================================================
# WALLET MODEL
# ============================================================

put("ledger/wallet_models.py", r'''
from django.contrib.auth.models import User
from django.db import models


class Wallet(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="wallets",
    )

    currency = models.CharField(
        max_length=10,
        default="USD",
    )

    ledger_account = models.OneToOneField(
        "ledger.LedgerAccount",
        on_delete=models.PROTECT,
        related_name="wallet",
    )

    active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "currency"],
                name="unique_user_wallet_currency",
            )
        ]

    def __str__(self):
        return f"{self.user.username} - {self.currency}"
''')


# ============================================================
# WALLET ADMIN
# ============================================================

put("ledger/wallet_admin.py", r'''
from django.contrib import admin

from .wallet_models import Wallet


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "currency",
        "ledger_account",
        "active",
        "created_at",
    )

    list_filter = (
        "currency",
        "active",
    )

    search_fields = (
        "user__username",
    )
''')


# ============================================================
# LEDGER MODEL IMPORT
# ============================================================

put("ledger/__init__.py", r'''
''')


# ============================================================
# ESCROW SERVICE
# ============================================================

put("escrow/services.py", r'''
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from ledger.models import LedgerAccount, LedgerEntry
from ledger.services import create_transaction

from .models import Escrow


@transaction.atomic
def release_escrow(escrow_id):
    escrow = (
        Escrow.objects
        .select_for_update()
        .select_related("order", "order__product")
        .get(pk=escrow_id)
    )

    if escrow.status != Escrow.HOLDING:
        raise ValueError(
            f"Escrow cannot be released from status: {escrow.status}"
        )

    order = escrow.order

    amount = Decimal(str(escrow.amount))

    escrow_account = LedgerAccount.objects.get(
        name="ESCROW",
        currency=escrow.currency,
    )

    seller_account = LedgerAccount.objects.get(
        name=f"SELLER:{order.product.seller_id}",
        currency=escrow.currency,
    )

    create_transaction(
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
            "order_id": order.pk,
        },
    )

    escrow.status = Escrow.RELEASED
    escrow.released_at = timezone.now()
    escrow.save(
        update_fields=[
            "status",
            "released_at",
        ]
    )

    order.status = order.COMPLETED
    order.save(update_fields=["status"])

    return escrow


@transaction.atomic
def refund_escrow(escrow_id):
    escrow = (
        Escrow.objects
        .select_for_update()
        .select_related("order")
        .get(pk=escrow_id)
    )

    if escrow.status != Escrow.HOLDING:
        raise ValueError(
            f"Escrow cannot be refunded from status: {escrow.status}"
        )

    order = escrow.order

    amount = Decimal(str(escrow.amount))

    escrow_account = LedgerAccount.objects.get(
        name="ESCROW",
        currency=escrow.currency,
    )

    buyer_account = LedgerAccount.objects.get(
        name=f"BUYER:{order.buyer_id}",
        currency=escrow.currency,
    )

    create_transaction(
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
            "order_id": order.pk,
        },
    )

    escrow.status = Escrow.REFUNDED
    escrow.save(update_fields=["status"])

    order.status = order.REFUNDED
    order.save(update_fields=["status"])

    return escrow
''')


# ============================================================
# FINANCE MANAGEMENT COMMAND
# ============================================================

put("ledger/management/__init__.py", "")
put("ledger/management/commands/__init__.py", "")

put("ledger/management/commands/seed_finance.py", r'''
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from ledger.models import LedgerAccount
from ledger.wallet_models import Wallet


class Command(BaseCommand):
    help = "Create the basic local marketplace financial accounts"


    def handle(self, *args, **options):

        users = User.objects.all()

        currencies = ["USD"]

        for currency in currencies:

            LedgerAccount.objects.get_or_create(
                name="ESCROW",
                currency=currency,
                defaults={
                    "account_type": LedgerAccount.LIABILITY,
                },
            )

            LedgerAccount.objects.get_or_create(
                name="PLATFORM_REVENUE",
                currency=currency,
                defaults={
                    "account_type": LedgerAccount.REVENUE,
                },
            )

            LedgerAccount.objects.get_or_create(
                name="PAYMENT_CLEARING",
                currency=currency,
                defaults={
                    "account_type": LedgerAccount.ASSET,
                },
            )

            for user in users:

                account_type = LedgerAccount.LIABILITY

                account, _ = LedgerAccount.objects.get_or_create(
                    name=f"BUYER:{user.id}",
                    currency=currency,
                    defaults={
                        "account_type": account_type,
                    },
                )

                Wallet.objects.get_or_create(
                    user=user,
                    currency=currency,
                    defaults={
                        "ledger_account": account,
                    },
                )

                seller_account, _ = LedgerAccount.objects.get_or_create(
                    name=f"SELLER:{user.id}",
                    currency=currency,
                    defaults={
                        "account_type": LedgerAccount.LIABILITY,
                    },
                )

        self.stdout.write(
            self.style.SUCCESS(
                "Financial accounts initialized."
            )
        )
''')


# ============================================================
# FIX SETTINGS
# ============================================================

settings = ROOT / "config/settings.py"
s = settings.read_text()

if "'ledger.wallet_models'" not in s:
    # Django loads models.py, so import Wallet there.
    pass


# ============================================================
# IMPORT WALLET INTO MODELS
# ============================================================

put("ledger/models_wallet_import.py", r'''
from .wallet_models import Wallet
''')

# append import to ledger/models.py
ledger_models = ROOT / "ledger/models.py"
lm = ledger_models.read_text()

if "from .wallet_models import Wallet" not in lm:
    lm += "\n\nfrom .wallet_models import Wallet\n"
    ledger_models.write_text(lm)


# ============================================================
# ADMIN WALLET REGISTRATION
# ============================================================

admin_file = ROOT / "ledger/admin.py"
a = admin_file.read_text()

if "Wallet" not in a:
    a += "\nfrom .wallet_admin import WalletAdmin\n"
    admin_file.write_text(a)


# ============================================================
# MIGRATE
# ============================================================

print()
print("[*] Making migrations...")

import subprocess

subprocess.check_call(
    [sys.executable, "manage.py", "makemigrations"],
    cwd=ROOT,
)

print()
print("[*] Applying migrations...")

subprocess.check_call(
    [sys.executable, "manage.py", "migrate"],
    cwd=ROOT,
)

print()
print("[*] Creating financial accounts...")

subprocess.check_call(
    [sys.executable, "manage.py", "seed_finance"],
    cwd=ROOT,
)

print()
print("=" * 60)
print("FINANCE ENGINE READY")
print("=" * 60)
print()
print("Run:")
print("python3 manage.py runserver")
