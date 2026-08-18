from django.contrib.auth import get_user_model
from django.db.models import Avg

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from marketplace.models import Order, Product
from vendor_verification.services import get_vendor_verification
from reviews.models import Review
from reviews.services import create_review, edit_review


User = get_user_model()



@csrf_exempt
def create_product_api(request):
    """
    Create a product using the Telegram Mini App identity.

    Telegram.WebApp.initData is sent as the `init_data` field.
    The server validates the Telegram signature before identifying
    the Django user.
    """
    if request.method != "POST":
        return JsonResponse(
            {"error": "POST required"},
            status=405,
        )

    import hashlib
    import hmac
    import json
    import time
    from urllib.parse import parse_qsl

    init_data = request.POST.get("init_data", "").strip()

    if not init_data:
        return JsonResponse(
            {"error": "Telegram authentication required"},
            status=401,
        )

    # Telegram bot token must be configured in Django settings.
    from django.conf import settings

    bot_token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")

    if not bot_token:
        return JsonResponse(
            {"error": "TELEGRAM_BOT_TOKEN is not configured"},
            status=500,
        )

    try:
        parsed = dict(parse_qsl(init_data, keep_blank_values=True))
        received_hash = parsed.pop("hash", None)

        if not received_hash:
            raise ValueError("Missing Telegram hash")

        # Telegram Web App authentication algorithm.
        data_check_string = "\n".join(
            f"{key}={value}"
            for key, value in sorted(parsed.items())
        )

        secret_key = hmac.new(
            b"WebAppData",
            bot_token.encode(),
            hashlib.sha256,
        ).digest()

        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(
            calculated_hash,
            received_hash,
        ):
            raise ValueError("Invalid Telegram signature")

        # Prevent stale initData from being replayed.
        auth_date = int(parsed.get("auth_date", "0"))

        if not auth_date or abs(time.time() - auth_date) > 86400:
            raise ValueError("Telegram authentication expired")

        telegram_user_raw = parsed.get("user")

        if not telegram_user_raw:
            raise ValueError("Telegram user information missing")

        telegram_user = json.loads(telegram_user_raw)

    except Exception as exc:
        return JsonResponse(
            {
                "error": "Invalid Telegram authentication",
                "detail": str(exc),
            },
            status=401,
        )

    telegram_id = str(telegram_user.get("id", "")).strip()
    telegram_username = (
        telegram_user.get("username") or ""
    ).strip()

    if not telegram_id:
        return JsonResponse(
            {"error": "Telegram user ID missing"},
            status=401,
        )

    # --------------------------------------------------------
    # Locate the Django user.
    #
    # Existing development installations generally use the
    # Telegram username as the Django username. Prefer that.
    # If it does not exist, do NOT silently create an account.
    # Account provisioning/auth linking can be added separately.
    # --------------------------------------------------------

    seller = None

    if telegram_username:
        seller = User.objects.filter(
            username=telegram_username
        ).first()

    if seller is None:
        return JsonResponse(
            {
                "error": "Telegram account is not linked to a marketplace vendor",
                "telegram_username": telegram_username,
                "telegram_id": telegram_id,
            },
            status=403,
        )

    title = request.POST.get("title", "").strip()
    description = request.POST.get(
        "description",
        "",
    ).strip()

    price = request.POST.get("price", "").strip()

    currency = request.POST.get(
        "currency",
        "",
    ).strip().upper()

    image = request.FILES.get("image")

    if not title or not price or not currency:
        return JsonResponse(
            {
                "error":
                    "title, price and currency are required"
            },
            status=400,
        )

    # ISO-4217-style three-letter currency code.
    if (
        len(currency) != 3
        or not currency.isalpha()
    ):
        return JsonResponse(
            {"error": "Currency must be a valid 3-letter code"},
            status=400,
        )

    try:
        product = Product.objects.create(
            seller=seller,
            title=title,
            description=description,
            price=price,
            currency=currency,
            image=image,
            active=True,
        )

    except (ValueError, TypeError) as exc:
        return JsonResponse(
            {"error": str(exc)},
            status=400,
        )

    return JsonResponse(
        {
            "success": True,
            "product": {
                "id": product.id,
                "name": product.title,
                "description": product.description,
                "price": str(product.price),
                "currency": product.currency,
                "seller": product.seller.username,
                "seller_id": product.seller_id,
                "image": (
                    request.build_absolute_uri(
                        product.image.url
                    )
                    if product.image
                    else None
                ),
            },
        },
        status=201,
    )


def products(request):
    result = []

    for product in Product.objects.select_related("seller").filter(
        active=True
    ).order_by("-id"):

        result.append({
            "id": product.id,
            "name": product.title,
            "description": product.description,
            "price": str(product.price),
            "currency": product.currency,
            "seller": product.seller.username,
            "seller_id": product.seller_id,
            "image": (
                request.build_absolute_uri(product.image.url)
                if product.image
                else None
            ),
        })

    return JsonResponse({"products": result})


def orders(request):
    username = request.GET.get("username")

    if not username:
        return JsonResponse({"orders": []})

    user = User.objects.filter(username=username).first()

    if not user:
        return JsonResponse({"orders": []})

    result = []

    for order in (
        Order.objects
        .filter(buyer=user)
        .select_related("product")
        .order_by("-id")
    ):
        review = Review.objects.filter(
            order=order
        ).first()

        result.append({
            "id": order.id,
            "product": order.product.title,
            "amount": str(order.amount),
            "currency": order.currency,
            "status": order.status,
            "reviewed": review is not None,
            "review_id": review.id if review else None,
            "review_rating": review.rating if review else None,
            "review_comment": review.comment if review else None,
            "review_edited": review.edited if review else False,
            "can_review": (
                order.status == Order.COMPLETED
                and review is None
            ),
        })

    return JsonResponse({"orders": result})


def vendor_profile(request, seller_id):
    seller = User.objects.filter(
        id=seller_id
    ).first()

    if not seller:
        return JsonResponse(
            {"error": "Vendor not found"},
            status=404,
        )

    verification = get_vendor_verification(seller)

    completed_orders = Order.objects.filter(
        product__seller=seller,
        status=Order.COMPLETED,
    ).count()

    refunded_orders = Order.objects.filter(
        product__seller=seller,
        status=Order.REFUNDED,
    ).count()

    review_qs = Review.objects.filter(
        seller=seller
    )

    review_count = review_qs.count()

    average_rating = review_qs.aggregate(
        average=Avg("rating")
    )["average"]

    if average_rating is not None:
        average_rating = round(
            float(average_rating),
            2,
        )

    reviews = []

    for review in review_qs.select_related(
        "buyer",
        "order",
    )[:20]:

        reviews.append({
            "id": review.id,
            "buyer": review.buyer.username,
            "rating": review.rating,
            "comment": review.comment,
            "edited": review.edited,
            "created_at": review.created_at.isoformat(),
            "updated_at": review.updated_at.isoformat(),
        })

    return JsonResponse({
        "seller": {
            "id": seller.id,
            "username": seller.username,
        },
        "verification": {
            "status": verification.status,
            "badge": verification.badge,
            "badge_level": verification.badge_level,
        },
        "stats": {
            "completed_transactions": completed_orders,
            "refunded_transactions": refunded_orders,
            "review_count": review_count,
            "average_rating": average_rating,
        },
        "reviews": reviews,
    })


@csrf_exempt
def create_review_api(request):
    if request.method != "POST":
        return JsonResponse(
            {"error": "POST required"},
            status=405,
        )

    username = request.POST.get("username")
    order_id = request.POST.get("order_id")
    rating = request.POST.get("rating")
    comment = request.POST.get("comment", "")

    if not username or not order_id or not rating:
        return JsonResponse(
            {"error": "username, order_id and rating are required"},
            status=400,
        )

    buyer = User.objects.filter(
        username=username
    ).first()

    if not buyer:
        return JsonResponse(
            {"error": "Buyer not found"},
            status=404,
        )

    try:
        rating = int(rating)

        if rating < 1 or rating > 5:
            raise ValueError("Rating must be between 1 and 5")

        review = create_review(
            buyer=buyer,
            order_id=int(order_id),
            rating=rating,
            comment=comment,
        )

    except (ValueError, TypeError) as exc:
        return JsonResponse(
            {"error": str(exc)},
            status=400,
        )

    return JsonResponse({
        "success": True,
        "review": {
            "id": review.id,
            "rating": review.rating,
            "comment": review.comment,
            "edited": review.edited,
        },
    }, status=201)


@csrf_exempt
def edit_review_api(request, review_id):
    if request.method != "POST":
        return JsonResponse(
            {"error": "POST required"},
            status=405,
        )

    username = request.POST.get("username")
    rating = request.POST.get("rating")
    comment = request.POST.get("comment", "")

    if not username or not rating:
        return JsonResponse(
            {"error": "username and rating are required"},
            status=400,
        )

    buyer = User.objects.filter(
        username=username
    ).first()

    if not buyer:
        return JsonResponse(
            {"error": "Buyer not found"},
            status=404,
        )

    try:
        review = edit_review(
            buyer=buyer,
            review_id=review_id,
            rating=int(rating),
            comment=comment,
        )

    except (ValueError, TypeError) as exc:
        return JsonResponse(
            {"error": str(exc)},
            status=400,
        )

    return JsonResponse({
        "success": True,
        "review": {
            "id": review.id,
            "rating": review.rating,
            "comment": review.comment,
            "edited": review.edited,
        },
    })
