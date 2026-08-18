import uuid
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

        telegram_id = 888000000 + uuid.uuid4().int % 1000000
        username = f"bot_test_{uuid.uuid4().hex[:10]}"

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
