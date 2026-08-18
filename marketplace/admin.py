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
