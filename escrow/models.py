from django.db import models
from marketplace.models import Order


class Escrow(models.Model):
    HOLDING = "holding"
    RELEASED = "released"
    REFUNDED = "refunded"
    DISPUTED = "disputed"

    STATUS_CHOICES = [
        (HOLDING, "Holding"),
        (RELEASED, "Released"),
        (REFUNDED, "Refunded"),
        (DISPUTED, "Disputed"),
    ]

    order = models.OneToOneField(
        Order,
        on_delete=models.PROTECT,
    )

    amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
    )

    currency = models.CharField(
        max_length=10,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=HOLDING,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    released_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    def __str__(self):
        return f"Escrow #{self.pk}"
