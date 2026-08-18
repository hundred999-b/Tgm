from django.contrib import admin, messages
from django.utils import timezone

from .models import VendorVerification


@admin.register(VendorVerification)
class VendorVerificationAdmin(admin.ModelAdmin):

    list_display = (
        "seller",
        "premium_badge",
        "status",
        "identity_verified",
        "business_verified",
        "payment_history_verified",
        "transaction_history_verified",
        "verified_by",
        "verified_at",
    )

    list_filter = (
        "status",
        "identity_verified",
        "business_verified",
        "payment_history_verified",
        "transaction_history_verified",
    )

    search_fields = (
        "seller__username",
        "seller__email",
        "notes",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "verified_at",
        "revoked_at",
        "verified_by",
        "premium_badge",
    )

    fieldsets = (
        (
            "Vendor",
            {
                "fields": (
                    "seller",
                    "status",
                    "premium_badge",
                )
            },
        ),
        (
            "Verification Checks",
            {
                "fields": (
                    "identity_verified",
                    "business_verified",
                    "payment_history_verified",
                    "transaction_history_verified",
                )
            },
        ),
        (
            "Review",
            {
                "fields": (
                    "notes",
                    "verified_by",
                    "verified_at",
                    "revoked_at",
                )
            },
        ),
        (
            "System",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    actions = (
        "mark_verified",
        "mark_trusted",
        "suspend_vendor",
        "revoke_verification",
    )

    @admin.display(description="Badge")
    def premium_badge(self, obj):
        labels = {
            VendorVerification.PENDING: "Pending",
            VendorVerification.VERIFIED: "Verified",
            VendorVerification.TRUSTED: "Trusted",
            VendorVerification.SUSPENDED: "Suspended",
            VendorVerification.REVOKED: "Revoked",
        }

        return labels.get(obj.status, "Pending")

    def _apply_status(self, queryset, status, request):
        count = 0

        for verification in queryset:
            verification.status = status

            if status in (
                VendorVerification.VERIFIED,
                VendorVerification.TRUSTED,
            ):
                verification.verified_at = timezone.now()
                verification.revoked_at = None
                verification.verified_by = request.user

            elif status == VendorVerification.SUSPENDED:
                verification.verified_by = request.user

            elif status == VendorVerification.REVOKED:
                verification.revoked_at = timezone.now()
                verification.verified_by = request.user

            verification.save()
            count += 1

        self.message_user(
            request,
            f"{count} vendor verification record(s) updated.",
            messages.SUCCESS,
        )

    @admin.action(description="Approve as Verified")
    def mark_verified(self, request, queryset):
        self._apply_status(
            queryset,
            VendorVerification.VERIFIED,
            request,
        )

    @admin.action(description="Promote to Trusted Vendor")
    def mark_trusted(self, request, queryset):
        self._apply_status(
            queryset,
            VendorVerification.TRUSTED,
            request,
        )

    @admin.action(description="Suspend Vendor")
    def suspend_vendor(self, request, queryset):
        self._apply_status(
            queryset,
            VendorVerification.SUSPENDED,
            request,
        )

    @admin.action(description="Revoke Verification")
    def revoke_verification(self, request, queryset):
        self._apply_status(
            queryset,
            VendorVerification.REVOKED,
            request,
        )
