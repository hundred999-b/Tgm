import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.conf import settings
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes


MINIAPP_URL = getattr(settings, "MINIAPP_URL", "").strip()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    text = (
        f"Welcome to the marketplace, {user.first_name or user.username or 'there'}!\n\n"
        "Browse products, publish products, manage orders and use your marketplace wallet."
    )

    if not MINIAPP_URL:
        await update.message.reply_text(
            text
            + "\n\nMini App is not configured yet. Set MINIAPP_URL in Django settings."
        )
        return

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🛍 Open Marketplace",
                web_app=WebAppInfo(url=MINIAPP_URL),
            )
        ]
    ])

    await update.message.reply_text(
        text,
        reply_markup=keyboard,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/start - Open marketplace\n"
        "/help - Show help"
    )


def main():
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", "").strip()

    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")

    if not MINIAPP_URL:
        raise RuntimeError(
            "MINIAPP_URL is not configured. "
            "Set it to the HTTPS URL of your Mini App."
        )

    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    print("Telegram marketplace bot starting...")
    print("Mini App:", MINIAPP_URL)

    application.run_polling()


if __name__ == "__main__":
    main()
