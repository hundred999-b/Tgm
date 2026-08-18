from pathlib import Path
import subprocess
import sys

ROOT = Path.cwd()

def put(name, text):
    p = ROOT / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text.strip() + "\n", encoding="utf-8")
    print("[+] " + name)

# ============================================================
# SETTINGS
# ============================================================

settings = ROOT / "config/settings.py"
s = settings.read_text()

apps = [
    "rest_framework",
    "accounts",
    "marketplace",
    "ledger",
    "payments",
    "escrow",
    "telegram_integration",
    "audit",
]

if '"accounts",' not in s:
    s = s.replace(
        '"django.contrib.staticfiles",',
        '"django.contrib.staticfiles",\n\n' +
        "\n".join(f'    "{x}",' for x in apps)
    )

settings.write_text(s, encoding="utf-8")

# ============================================================
# ACCOUNTS
# ============================================================

put("accounts/models.py", r'''
from django.contrib.auth.models import User
from django.db import models


class Profile(models.Model):
    BUYER = "buyer"
    SELLER = "seller"

    ROLE_CHOICES = [
        (BUYER, "Buyer"),
        (SELLER, "Seller"),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=BUYER,
    )

    phone = models.CharField(
        max_length=40,
        blank=True,
    )

    country = models.CharField(
        max_length=100,
        blank=True,
    )

    verified = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return f"{self.user.username} - {self.role}"
''')

put("accounts/admin.py", r'''
from django.contrib import admin
from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "role",
        "country",
        "verified",
        "created_at",
    )

    list_filter = (
        "role",
        "verified",
        "country",
    )

    search_fields = (
        "user__username",
        "user__email",
        "phone",
        "country",
    )
''')

# ============================================================
# MARKETPLACE
# ============================================================

put("marketplace/models.py", r'''
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
''')

put("marketplace/admin.py", r'''
from django.contrib import admin
from .models import Product, Order


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "seller",
        "price",
        "currency",
        "active",
        "created_at",
    )

    list_filter = (
        "active",
        "currency",
    )

    search_fields = (
        "title",
        "description",
        "seller__username",
    )


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "buyer",
        "product",
        "amount",
        "currency",
        "status",
        "created_at",
    )

    list_filter = (
        "status",
        "currency",
    )
''')

# ============================================================
# LEDGER
# ============================================================

put("ledger/models.py", r'''
from django.core.validators import MinValueValidator
from django.db import models


class LedgerAccount(models.Model):
    ASSET = "asset"
    LIABILITY = "liability"
    REVENUE = "revenue"
    EXPENSE = "expense"
    EQUITY = "equity"

    TYPES = [
        (ASSET, "Asset"),
        (LIABILITY, "Liability"),
        (REVENUE, "Revenue"),
        (EXPENSE, "Expense"),
        (EQUITY, "Equity"),
    ]

    name = models.CharField(max_length=120)

    account_type = models.CharField(
        max_length=20,
        choices=TYPES,
    )

    currency = models.CharField(
        max_length=10,
        default="USD",
    )

    active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} [{self.currency}]"


class LedgerTransaction(models.Model):
    transaction_id = models.CharField(
        max_length=64,
        unique=True,
    )

    description = models.CharField(
        max_length=255,
    )

    reference = models.CharField(
        max_length=120,
        blank=True,
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return self.transaction_id


class LedgerEntry(models.Model):
    DEBIT = "debit"
    CREDIT = "credit"

    DIRECTIONS = [
        (DEBIT, "Debit"),
        (CREDIT, "Credit"),
    ]

    transaction = models.ForeignKey(
        LedgerTransaction,
        on_delete=models.PROTECT,
        related_name="entries",
    )

    account = models.ForeignKey(
        LedgerAccount,
        on_delete=models.PROTECT,
        related_name="entries",
    )

    amount = models.DecimalField(
        max_digits=24,
        decimal_places=8,
        validators=[MinValueValidator(0)],
    )

    direction = models.CharField(
        max_length=6,
        choices=DIRECTIONS,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name="ledger_entry_positive",
            )
        ]
''')

put("ledger/admin.py", r'''
from django.contrib import admin
from .models import (
    LedgerAccount,
    LedgerTransaction,
    LedgerEntry,
)

admin.site.register(LedgerAccount)
admin.site.register(LedgerTransaction)
admin.site.register(LedgerEntry)
''')

# ============================================================
# PAYMENTS
# ============================================================

put("payments/models.py", r'''
from django.db import models


class Payment(models.Model):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"

    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (SUCCEEDED, "Succeeded"),
        (FAILED, "Failed"),
        (REFUNDED, "Refunded"),
    ]

    provider = models.CharField(
        max_length=80,
    )

    provider_reference = models.CharField(
        max_length=160,
        unique=True,
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

    idempotency_key = models.CharField(
        max_length=160,
        unique=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return f"{self.provider}:{self.provider_reference}"
''')

put("payments/admin.py", r'''
from django.contrib import admin
from .models import Payment

admin.site.register(Payment)
''')

# ============================================================
# ESCROW
# ============================================================

put("escrow/models.py", r'''
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
''')

put("escrow/admin.py", r'''
from django.contrib import admin
from .models import Escrow

admin.site.register(Escrow)
''')

# ============================================================
# TELEGRAM
# ============================================================

put("telegram_integration/models.py", r'''
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
''')

put("telegram_integration/admin.py", r'''
from django.contrib import admin
from .models import TelegramAccount

admin.site.register(TelegramAccount)
''')

# ============================================================
# AUDIT
# ============================================================

put("audit/models.py", r'''
from django.contrib.auth.models import User
from django.db import models


class AuditEvent(models.Model):
    actor = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    action = models.CharField(
        max_length=120,
    )

    object_type = models.CharField(
        max_length=120,
        blank=True,
    )

    object_id = models.CharField(
        max_length=120,
        blank=True,
    )

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return f"{self.action} @ {self.created_at}"
''')

put("audit/admin.py", r'''
from django.contrib import admin
from .models import AuditEvent

admin.site.register(AuditEvent)
''')

# ============================================================
# MIGRATIONS
# ============================================================

print()
print("[*] Creating migrations...")

subprocess.check_call(
    [sys.executable, "manage.py", "makemigrations"],
    cwd=ROOT,
)

print()
print("[*] Applying migrations...")

subprocess.check_call(
    [sys.executable, "manage.py", "migrate"],
    cwd=ROOT,
)

print()
print("=" * 60)
print("MARKETPLACE CORE BUILT")
print("=" * 60)
print()
print("Start:")
print("python3 manage.py runserver")
print()
print("Admin:")
print("http://127.0.0.1:8000/admin/")
print()
