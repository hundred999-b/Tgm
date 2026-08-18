from django.db import transaction

from marketplace.models import Order
from .models import Review


@transaction.atomic
def create_review(*, buyer, order_id, rating, comment=""):
    order = (
        Order.objects
        .select_for_update()
        .select_related("product", "product__seller")
        .get(pk=order_id)
    )

    if order.buyer_id != buyer.id:
        raise ValueError("Only the buyer can review this order.")

    if order.status != Order.COMPLETED:
        raise ValueError(
            "A review is only available after the order is completed "
            "and the seller has been paid."
        )

    seller = order.product.seller

    if seller_id := getattr(order, "seller_id", None):
        if seller_id != seller.id:
            raise ValueError("Invalid seller relationship.")

    if Review.objects.filter(order=order).exists():
        raise ValueError("This transaction has already been reviewed.")

    return Review.objects.create(
        buyer=buyer,
        seller=seller,
        order=order,
        rating=rating,
        comment=comment.strip(),
    )


@transaction.atomic
def edit_review(*, buyer, review_id, rating, comment=""):
    review = (
        Review.objects
        .select_for_update()
        .get(pk=review_id)
    )

    if review.buyer_id != buyer.id:
        raise ValueError("Only the original buyer can edit this review.")

    review.rating = rating
    review.comment = comment.strip()
    review.edited = True
    review.save(update_fields=[
        "rating",
        "comment",
        "edited",
        "updated_at",
    ])

    return review
