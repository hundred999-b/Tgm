from django.utils import timezone

from .models import VendorVerification


def get_vendor_verification(seller):
    verification, _ = VendorVerification.objects.get_or_create(
        seller=seller
    )
    return verification


def set_vendor_status(
    seller,
    status,
    *,
    identity_verified=None,
    business_verified=None,
    payment_history_verified=None,
    transaction_history_verified=None,
    note="",
):
    verification = get_vendor_verification(seller)

    verification.status = status

    if identity_verified is not None:
        verification.identity_verified = identity_verified

    if business_verified is not None:
        verification.business_verified = business_verified

    if payment_history_verified is not None:
        verification.payment_history_verified = payment_history_verified

    if transaction_history_verified is not None:
        verification.transaction_history_verified = transaction_history_verified

    if note:
        verification.notes = note

    now = timezone.now()

    if status in (
        VendorVerification.VERIFIED,
        VendorVerification.TRUSTED,
    ):
        verification.verified_at = now
        verification.revoked_at = None

    elif status == VendorVerification.REVOKED:
        verification.revoked_at = now

    verification.save()

    return verification
