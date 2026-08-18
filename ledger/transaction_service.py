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
                "account": buyer_account,
                "direction": LedgerEntry.DEBIT,
                "amount": amount,
            },
            {
                "account": clearing,
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
                "direction": LedgerEntry.CREDIT,
                "amount": amount,
            },
            {
                "account": escrow_account,
                "direction": LedgerEntry.DEBIT,
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
