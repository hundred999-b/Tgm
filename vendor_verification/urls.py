from django.urls import path

from . import api

urlpatterns = [
    path(
        "<int:seller_id>/",
        api.vendor_profile,
        name="vendor-profile",
    ),
]
