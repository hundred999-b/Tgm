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
