from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .models import VendorVerification

User = get_user_model()


@require_GET
def vendor_profile(request, seller_id):
    seller = (
        User.objects
        .filter(pk=seller_id)
        .first()
    )

    if not seller:
        return JsonResponse(
            {"error": "Seller not found"},
            status=404,
        )

    verification = (
        VendorVerification.objects
        .filter(seller=seller)
        .first()
    )

    data = {
        "seller": {
            "id": seller.id,
            "username": seller.username,
        },
        "verification": {
            "status": (
                verification.status
                if verification
                else "pending"
            ),
            "badge": (
                verification.badge
                if verification
                else ""
            ),
            "badge_level": (
                verification.badge_level
                if verification
                else "pending"
            ),
            "identity_verified": (
                verification.identity_verified
                if verification
                else False
            ),
            "business_verified": (
                verification.business_verified
                if verification
                else False
            ),
            "payment_history_verified": (
                verification.payment_history_verified
                if verification
                else False
            ),
            "transaction_history_verified": (
                verification.transaction_history_verified
                if verification
                else False
            ),
        },
    }

    return JsonResponse(data)
