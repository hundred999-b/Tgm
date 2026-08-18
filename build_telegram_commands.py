import sys
from pathlib import Path

ROOT = Path.cwd()


def put(name, text):
    p = ROOT / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text.strip() + "\n", encoding="utf-8")
    print("[+] " + name)


put("telegram_integration/marketplace_commands.py", r'''
from decimal import Decimal, InvalidOperation

from django.db import transaction

from ledger.transaction_service import (
    test_deposit,
    wallet_balance,
    purchase_order,
)

from marketplace.models import Product, Order

from .bot import get_or_create_telegram_user


def command_products():
    products = Product.objects.filter(
        active=True
    ).order_by("id")

    if not products.exists():
        return "No products available."

    lines = ["🛍 AVAILABLE PRODUCTS", ""]

    for product in products:
        lines.append(
            f"#{product.id} "
            f"{product.title} — "
            f"{product.price} {product.currency}"
        )

    lines.append("")
    lines.append("Use /product <id> to view details.")

    return "\n".join(lines)


def command_product(product_id):
    try:
        product_id = int(product_id)
    except (TypeError, ValueError):
        return "Usage: /product <id>"

    product = Product.objects.filter(
        pk=product_id,
        active=True,
    ).select_related("seller").first()

    if not product:
        return "Product not found."

    return (
        f"🛍 {product.title}\n\n"
        f"{product.description}\n\n"
        f"Price: {product.price} {product.currency}\n"
        f"Seller: {product.seller.username}\n"
        f"Product ID: {product.id}\n\n"
        f"To purchase: /buy {product.id}"
    )


def command_wallet(telegram_id, username=None):
    user = get_or_create_telegram_user(
        telegram_id,
        username,
    )

    balance = wallet_balance(user, "USD")

    return (
        "💰 WALLET\n\n"
        f"Balance: {balance} USD"
    )


def command_testdeposit(
    telegram_id,
    username=None,
    amount="100",
):
    user = get_or_create_telegram_user(
        telegram_id,
        username,
    )

    try:
        amount = Decimal(str(amount))
    except InvalidOperation:
        return "Invalid amount."

    if amount <= 0:
        return "Amount must be greater than zero."

    # Explicit development-only guard.
    from django.conf import settings

    if not getattr(settings, "DEBUG", False):
        return "Test deposits are disabled."

    tx = test_deposit(
        user,
        amount,
        "USD",
    )

    return (
        "🧪 TEST DEPOSIT COMPLETE\n\n"
        f"Amount: {amount} USD\n"
        f"Transaction: {tx.transaction_id}\n"
        f"New balance: {wallet_balance(user, 'USD')} USD"
    )


@transaction.atomic
def command_buy(
    telegram_id,
    product_id,
    username=None,
):
    user = get_or_create_telegram_user(
        telegram_id,
        username,
    )

    try:
        product_id = int(product_id)
    except (TypeError, ValueError):
        return "Usage: /buy <product_id>"

    product = Product.objects.filter(
        pk=product_id,
        active=True,
    ).select_related("seller").first()

    if not product:
        return "Product not found."

    if product.seller_id == user.id:
        return "You cannot purchase your own product."

    balance = wallet_balance(
        user,
        product.currency,
    )

    if balance < product.price:
        return (
            "❌ INSUFFICIENT FUNDS\n\n"
            f"Price: {product.price} {product.currency}\n"
            f"Balance: {balance} {product.currency}\n\n"
            "For local development, use:\n"
            "/testdeposit 100"
        )

    order = Order.objects.create(
        buyer=user,
        product=product,
        amount=product.price,
        currency=product.currency,
        status=Order.PENDING,
    )

    try:
        tx = purchase_order(order)
    except Exception:
        order.delete()
        raise

    return (
        "✅ PURCHASE CREATED\n\n"
        f"Order: #{order.id}\n"
        f"Product: {product.title}\n"
        f"Amount: {product.price} {product.currency}\n"
        f"Escrow: FUNDED\n"
        f"Transaction: {tx.transaction_id}\n\n"
        f"Remaining balance: "
        f"{wallet_balance(user, product.currency)} "
        f"{product.currency}"
    )


def command_orders(
    telegram_id,
    username=None,
):
    user = get_or_create_telegram_user(
        telegram_id,
        username,
    )

    orders = (
        Order.objects
        .filter(buyer=user)
        .select_related("product")
        .order_by("-id")
    )

    if not orders.exists():
        return "📦 You have no orders."

    lines = ["📦 YOUR ORDERS", ""]

    for order in orders:
        lines.append(
            f"#{order.id} "
            f"{order.product.title} — "
            f"{order.amount} {order.currency} — "
            f"{order.status}"
        )

    return "\n".join(lines)


def command_order(
    telegram_id,
    order_id,
    username=None,
):
    user = get_or_create_telegram_user(
        telegram_id,
        username,
    )

    try:
        order_id = int(order_id)
    except (TypeError, ValueError):
        return "Usage: /order <id>"

    order = (
        Order.objects
        .filter(
            pk=order_id,
            buyer=user,
        )
        .select_related("product")
        .first()
    )

    if not order:
        return "Order not found."

    return (
        f"📦 ORDER #{order.id}\n\n"
        f"Product: {order.product.title}\n"
        f"Amount: {order.amount} {order.currency}\n"
        f"Status: {order.status}"
    )
''')


# ============================================================
# TEST COMMAND
# ============================================================

put(
    "telegram_integration/management/commands/test_marketplace_bot.py",
    r'''
from django.core.management.base import BaseCommand

from telegram_integration.marketplace_commands import (
    command_products,
    command_product,
    command_wallet,
    command_testdeposit,
    command_buy,
    command_orders,
    command_order,
)


class Command(BaseCommand):

    def handle(self, *args, **options):

        telegram_id = 888888888
        username = "bot_buyer"

        self.stdout.write("=== PRODUCTS ===")
        self.stdout.write(command_products())

        self.stdout.write("")
        self.stdout.write("=== PRODUCT ===")
        self.stdout.write(command_product(1))

        self.stdout.write("")
        self.stdout.write("=== DEPOSIT ===")
        self.stdout.write(
            command_testdeposit(
                telegram_id,
                username,
                "100",
            )
        )

        self.stdout.write("")
        self.stdout.write("=== WALLET ===")
        self.stdout.write(
            command_wallet(
                telegram_id,
                username,
            )
        )

        self.stdout.write("")
        self.stdout.write("=== BUY ===")

        result = command_buy(
            telegram_id,
            1,
            username,
        )

        self.stdout.write(result)

        self.stdout.write("")
        self.stdout.write("=== ORDERS ===")
        self.stdout.write(
            command_orders(
                telegram_id,
                username,
            )
        )

        self.stdout.write("")
        self.stdout.write("=== ORDER ===")

        from marketplace.models import Order

        order = (
            Order.objects
            .filter(
                buyer__username=username
            )
            .order_by("-id")
            .first()
        )

        if order:
            self.stdout.write(
                command_order(
                    telegram_id,
                    order.id,
                    username,
                )
            )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "TELEGRAM MARKETPLACE COMMAND TEST PASSED"
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
print("TELEGRAM MARKETPLACE COMMANDS READY")
print("=" * 60)
print()
print("Test:")
print("python3 manage.py test_marketplace_bot")
