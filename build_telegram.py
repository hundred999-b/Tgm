import sys
from pathlib import Path

ROOT = Path.cwd()


def put(name, text):
    p = ROOT / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text.strip() + "\n", encoding="utf-8")
    print("[+] " + name)


# ============================================================
# TELEGRAM SERVICE
# ============================================================

put("telegram_integration/bot.py", r'''
import os
import django

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings",
)

django.setup()

from django.contrib.auth.models import User
from marketplace.models import Product, Order
from ledger.transaction_service import wallet_balance


def get_or_create_telegram_user(
    telegram_user_id,
    username=None,
):
    """
    Development mapping between a Telegram identity
    and a Django user.

    Production authentication/verification will be added later.
    """

    from .models import TelegramAccount

    account = TelegramAccount.objects.filter(
        telegram_user_id=telegram_user_id
    ).select_related("user").first()

    if account:
        if username and account.username != username:
            account.username = username
            account.save(update_fields=["username"])

        return account.user

    base = username or f"telegram_{telegram_user_id}"

    clean = "".join(
        c for c in base
        if c.isalnum() or c in "_-"
    )[:120]

    if not clean:
        clean = f"telegram_{telegram_user_id}"

    candidate = clean
    counter = 1

    while User.objects.filter(username=candidate).exists():
        candidate = f"{clean}_{counter}"
        counter += 1

    user = User.objects.create_user(
        username=candidate,
    )

    TelegramAccount.objects.create(
        user=user,
        telegram_user_id=telegram_user_id,
        username=username or "",
        verified=False,
    )

    return user


def products():
    return list(
        Product.objects.filter(
            active=True
        ).select_related("seller")
    )


def product_details(product_id):
    return Product.objects.filter(
        pk=product_id,
        active=True,
    ).select_related("seller").first()


def user_orders(user):
    return list(
        Order.objects.filter(
            buyer=user
        ).select_related(
            "product"
        ).order_by("-created_at")
    )


def user_wallet(user):
    return wallet_balance(
        user,
        "USD",
    )
''')


# ============================================================
# BOT COMMAND HANDLER
# ============================================================

put("telegram_integration/handlers.py", r'''
from .bot import (
    get_or_create_telegram_user,
    products,
    product_details,
    user_orders,
    user_wallet,
)


def start(
    telegram_user_id,
    username=None,
):
    user = get_or_create_telegram_user(
        telegram_user_id,
        username,
    )

    return (
        f"Welcome to the marketplace, "
        f"{user.username}.\n\n"
        "Commands:\n"
        "/products - browse products\n"
        "/wallet - view wallet\n"
        "/orders - view orders\n"
        "/help - show help"
    )


def help_text():
    return (
        "Marketplace commands:\n\n"
        "/products\n"
        "/wallet\n"
        "/orders\n"
        "/help"
    )


def product_list():
    items = products()

    if not items:
        return "No products are currently available."

    lines = ["AVAILABLE PRODUCTS", ""]

    for product in items:
        lines.append(
            f"#{product.id} "
            f"{product.title} — "
            f"{product.price} {product.currency}"
        )

    lines.append("")
    lines.append(
        "Use /product ID to view a product."
    )

    return "\n".join(lines)


def product_info(product_id):
    product = product_details(product_id)

    if not product:
        return "Product not found."

    return (
        f"{product.title}\n\n"
        f"{product.description}\n\n"
        f"Price: {product.price} {product.currency}\n"
        f"Seller: {product.seller.username}\n\n"
        f"ID: {product.id}"
    )


def wallet_info(
    telegram_user_id,
    username=None,
):
    user = get_or_create_telegram_user(
        telegram_user_id,
        username,
    )

    balance = user_wallet(user)

    return (
        f"Wallet\n\n"
        f"Currency: USD\n"
        f"Balance: {balance}"
    )


def orders_info(
    telegram_user_id,
    username=None,
):
    user = get_or_create_telegram_user(
        telegram_user_id,
        username,
    )

    orders = user_orders(user)

    if not orders:
        return "You have no orders."

    lines = ["YOUR ORDERS", ""]

    for order in orders:
        lines.append(
            f"#{order.id} "
            f"{order.product.title} — "
            f"{order.amount} {order.currency} — "
            f"{order.status}"
        )

    return "\n".join(lines)
''')


# ============================================================
# DRY-RUN CLI
# ============================================================

put("telegram_integration/cli.py", r'''
import sys

import django

django.setup()

from .handlers import (
    start,
    help_text,
    product_list,
    product_info,
    wallet_info,
    orders_info,
)


def main():

    print("=" * 60)
    print("LOCAL TELEGRAM MARKETPLACE TEST CLIENT")
    print("=" * 60)
    print()

    telegram_id = 999999999
    username = "local_test_user"

    print(start(
        telegram_id,
        username,
    ))

    print()
    print(product_list())

    print()
    print(wallet_info(
        telegram_id,
        username,
    ))

    print()
    print(orders_info(
        telegram_id,
        username,
    ))


if __name__ == "__main__":
    main()
''')


# ============================================================
# MANAGEMENT COMMAND
# ============================================================

put("telegram_integration/management/__init__.py", "")

put("telegram_integration/management/commands/__init__.py", "")

put(
    "telegram_integration/management/commands/test_telegram.py",
    r'''
from django.core.management.base import BaseCommand

from telegram_integration.handlers import (
    start,
    product_list,
    wallet_info,
    orders_info,
)


class Command(BaseCommand):

    def handle(self, *args, **options):

        telegram_id = 999999998
        username = "telegram_test"

        self.stdout.write(
            start(
                telegram_id,
                username,
            )
        )

        self.stdout.write("")
        self.stdout.write(product_list())

        self.stdout.write("")
        self.stdout.write(
            wallet_info(
                telegram_id,
                username,
            )
        )

        self.stdout.write("")
        self.stdout.write(
            orders_info(
                telegram_id,
                username,
            )
        )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "TELEGRAM INTEGRATION TEST PASSED"
            )
        )
''',
)


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
print("TELEGRAM MARKETPLACE INTEGRATION READY")
print("=" * 60)
print()
print("Test:")
print("python3 manage.py test_telegram")
