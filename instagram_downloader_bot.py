"""
Instagram Video Downloader — Telegram Bot
==========================================
"""

import os
import logging
import tempfile
import re

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import yt_dlp

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "SHU_YERGA_BOT_TOKENINGIZNI_YOZING")
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

INSTAGRAM_URL_PATTERN = re.compile(
    r"(https?://)?(www\.)?instagram\.com/(reel|reels|p|tv)/[A-Za-z0-9_\-]+"
)


def extract_instagram_url(text: str):
    match = INSTAGRAM_URL_PATTERN.search(text)
    if not match:
        return None
    return match.group(0)


def download_instagram_video(url: str, output_dir: str) -> str:
    output_template = os.path.join(output_dir, "%(id)s.%(ext)s")
    ydl_opts = {
        "outtmpl": output_template,
        "format": "mp4/best",
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filepath = ydl.prepare_filename(info)
        return filepath


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Salom! 👋\n\n"
        "Menga Instagram video/reels linkini yuboring, men uni yuklab "
        "sizga qaytaraman.\n\n"
        "Masalan: https://www.instagram.com/reel/XXXXXXXXXXX/"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📌 Foydalanish:\n"
        "1. Instagram'dan video/reels linkini nusxalang\n"
        "2. Shu botga yuboring\n"
        "3. Bir necha soniyada video sizga qaytariladi\n\n"
        "Eslatma: faqat ochiq (public) postlar yuklanadi."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text or ""
    url = extract_instagram_url(text)

    if not url:
        await update.message.reply_text(
            "Bu Instagram link ko'rinmayapti 🤔\n"
            "Iltimos, reel yoki post havolasini yuboring."
        )
        return

    status_msg = await update.message.reply_text("⏳ Video yuklanmoqda...")
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_VIDEO
    )

    with tempfile.TemporaryDirectory() as tmp_dir:
        try:
            filepath = download_instagram_video(url, tmp_dir)
        except yt_dlp.utils.DownloadError as e:
            logger.error("Download error: %s", e)
            await status_msg.edit_text(
                "❌ Video yuklab bo'lmadi.\n"
                "Sabab: link noto'g'ri, post yopiq (private) yoki "
                "o'chirilgan bo'lishi mumkin."
            )
            return
        except Exception as e:
            logger.exception("Kutilmagan xatolik")
            await status_msg.edit_text(f"❌ Xatolik yuz berdi: {e}")
            return

        if not os.path.exists(filepath):
            await status_msg.edit_text("❌ Video fayli topilmadi.")
            return

        file_size = os.path.getsize(filepath)
        if file_size > MAX_FILE_SIZE:
            await status_msg.edit_text(
                "❌ Video hajmi juda katta (Telegram cheklovi ~50MB). "
                "Bu videoni bot orqali yuborib bo'lmaydi."
            )
            return

        await status_msg.edit_text("📤 Yuborilmoqda...")
        try:
            with open(filepath, "rb") as video_file:
                await update.message.reply_video(
                    video=video_file,
                    caption="✅ Mana video!",
                    supports_streaming=True,
                )
            await status_msg.delete()
        except Exception as e:
            logger.exception("Yuborishda xatolik")
            await status_msg.edit_text(f"❌ Yuborishda xatolik: {e}")


def main() -> None:
    if BOT_TOKEN == "SHU_YERGA_BOT_TOKENINGIZNI_YOZING":
        raise SystemExit(
            "Iltimos, avval BOT_TOKEN ni sozlang."
        )

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot ishga tushdi...")
    app.run_polling()


if __name__ == "__main__":
    main()
