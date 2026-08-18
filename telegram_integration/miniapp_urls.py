from django.urls import path
from django.shortcuts import render
from . import miniapp_api

def index(request):
    return render(request, "miniapp/index.html")

urlpatterns = [
    path("", index, name="miniapp"),
    path("products/", miniapp_api.products, name="miniapp-products"),
    path("products/create/", miniapp_api.create_product_api, name="miniapp-product-create"),
    path("orders/", miniapp_api.orders, name="miniapp-orders"),
    path("vendor/<int:seller_id>/", miniapp_api.vendor_profile, name="miniapp-vendor"),
    path("reviews/create/", miniapp_api.create_review_api, name="miniapp-review-create"),
    path("reviews/<int:review_id>/edit/", miniapp_api.edit_review_api, name="miniapp-review-edit"),
]
