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
