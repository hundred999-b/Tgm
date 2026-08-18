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
