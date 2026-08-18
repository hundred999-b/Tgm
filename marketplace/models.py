from django.contrib.auth.models import User
from django.db import models


class Product(models.Model):
    seller = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="products",
    )

    title = models.CharField(max_length=200)

    description = models.TextField(blank=True)

    price = models.DecimalField(
        max_digits=18,
        decimal_places=2,
    )

    currency = models.CharField(
        max_length=10,
        default="USD",
    )

    image = models.ImageField(
        upload_to="products/",
        blank=True,
        null=True,
    )

    active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return self.title


class Order(models.Model):
    PENDING = "pending"
    PAID = "paid"
    ESCROW = "escrow"
    COMPLETED = "completed"
    REFUNDED = "refunded"
    DISPUTED = "disputed"

    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (PAID, "Paid"),
        (ESCROW, "Escrow"),
        (COMPLETED, "Completed"),
        (REFUNDED, "Refunded"),
        (DISPUTED, "Disputed"),
    ]

    buyer = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="marketplace_orders",
    )

    product = models.ForeignKey(
        Product,
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
        default=PENDING,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return f"Order #{self.pk}"
