from django.conf import settings
from django.db import models


class VendorVerification(models.Model):
    PENDING = "pending"
    VERIFIED = "verified"
    TRUSTED = "trusted"
    SUSPENDED = "suspended"
    REVOKED = "revoked"

    STATUSES = [
        (PENDING, "Pending"),
        (VERIFIED, "Verified"),
        (TRUSTED, "Trusted Vendor"),
        (SUSPENDED, "Suspended"),
        (REVOKED, "Revoked"),
    ]

    seller = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="vendor_verification",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUSES,
        default=PENDING,
    )

    identity_verified = models.BooleanField(default=False)
    business_verified = models.BooleanField(default=False)
    payment_history_verified = models.BooleanField(default=False)
    transaction_history_verified = models.BooleanField(default=False)

    notes = models.TextField(blank=True)

    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="vendor_verifications_performed",
    )

    verified_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_trusted(self):
        return self.status == self.TRUSTED

    @property
    def badge(self):
        return {
            self.VERIFIED: "Verified Vendor",
            self.TRUSTED: "Trusted Vendor",
            self.SUSPENDED: "Suspended",
            self.REVOKED: "Verification Revoked",
        }.get(self.status, "")

    @property
    def badge_level(self):
        return {
            self.VERIFIED: "verified",
            self.TRUSTED: "trusted",
            self.SUSPENDED: "suspended",
            self.REVOKED: "revoked",
            self.PENDING: "pending",
        }.get(self.status, "pending")

    def __str__(self):
        return f"{self.seller.username} — {self.get_status_display()}"
