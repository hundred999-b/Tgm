from django.contrib import admin
from .models import (
    LedgerAccount,
    LedgerTransaction,
    LedgerEntry,
)

admin.site.register(LedgerAccount)
admin.site.register(LedgerTransaction)
admin.site.register(LedgerEntry)

from .wallet_admin import WalletAdmin
