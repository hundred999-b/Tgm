from django.contrib.auth.models import User
from django.db import models


class TelegramAccount(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="telegram_account",
    )

    telegram_user_id = models.BigIntegerField(
        unique=True,
    )

    username = models.CharField(
        max_length=255,
        blank=True,
    )

    verified = models.BooleanField(
        default=False,
    )

    verified_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return self.username or str(self.telegram_user_id)
