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

    # Every marketplace buyer needs a corresponding
    # ledger account before wallet operations are possible.
    from ledger.models import LedgerAccount

    LedgerAccount.objects.get_or_create(
        name=f"BUYER:{user.id}",
        currency="USD",
        defaults={
            "account_type": LedgerAccount.ASSET,
        },
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
    from ledger.models import LedgerAccount

    LedgerAccount.objects.get_or_create(
        name=f"BUYER:{user.id}",
        currency="USD",
        defaults={
            "account_type": LedgerAccount.ASSET,
        },
    )

    return wallet_balance(
        user,
        "USD",
    )
