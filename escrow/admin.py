from django.contrib import admin, messages

from .models import Escrow
from .services import release_escrow, refund_escrow


@admin.register(Escrow)
class EscrowAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "order",
        "amount",
        "currency",
        "status",
        "created_at",
        "released_at",
    )

    list_filter = (
        "status",
        "currency",
    )

    search_fields = (
        "order__id",
        "order__buyer__username",
        "order__product__title",
    )

    actions = [
        "release_selected",
        "refund_selected",
    ]

    @admin.action(description="Release selected escrow")
    def release_selected(self, request, queryset):

        success = 0

        for escrow in queryset:

            try:
                release_escrow(
                    escrow.pk,
                    actor=request.user,
                )

                success += 1

            except Exception as exc:

                self.message_user(
                    request,
                    f"Escrow #{escrow.pk}: {exc}",
                    level=messages.ERROR,
                )

        if success:
            self.message_user(
                request,
                f"{success} escrow(s) released.",
                level=messages.SUCCESS,
            )

    @admin.action(description="Refund selected escrow")
    def refund_selected(self, request, queryset):

        success = 0

        for escrow in queryset:

            try:
                refund_escrow(
                    escrow.pk,
                    actor=request.user,
                )

                success += 1

            except Exception as exc:

                self.message_user(
                    request,
                    f"Escrow #{escrow.pk}: {exc}",
                    level=messages.ERROR,
                )

        if success:
            self.message_user(
                request,
                f"{success} escrow(s) refunded.",
                level=messages.SUCCESS,
            )
