import os
import requests
from flask import Flask, request
from pydub import AudioSegment
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler, ChatMemberHandler,
    ContextTypes, filters
)
import asyncio
import logging

# تنظیمات لاگ
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ====== تنظیمات ======
BOT_TOKEN = "7830811506:AAHviqGsjxf1S57-W46F5bu9Rh9kuZIQ-fY"  # توکن ربات تلگرام
GENIUS_API_TOKEN = "1k3ljpOFJhSQs52wnj8MaAnfFqVfLGOzBXUhBakw7aD1SAvQsVqih4RK8ds8CLNx"  # توکن API از Genius
SUDO_USERS = [5668163693 , 987654321]  # آیدی عددی سودوها
WEBHOOK_URL = "https://music-xirm.onrender.com/webhook"

# ====== راه‌اندازی Flask ======
app = Flask(__name__)
application = Application.builder().token(BOT_TOKEN).build()

# ====== بررسی سودو ======
def is_sudo(user_id):
    return user_id in SUDO_USERS

# ====== برش یک دقیقه از آهنگ ======
def create_demo(file_path):
    try:
        audio = AudioSegment.from_file(file_path)
        demo_file = "demo.ogg"
        audio[:60000].export(demo_file, format="ogg", codec="libopus")
        return demo_file
    except Exception as e:
        logger.error(f"Error creating demo: {e}")
        return None

# ====== دریافت لیریک از Genius ======
def get_lyrics(song_name):
    try:
        headers = {"Authorization": f"Bearer {GENIUS_API_TOKEN}"}
        response = requests.get("https://api.genius.com/search", headers=headers, params={"q": song_name})

        if response.status_code == 200:
            hits = response.json().get("response", {}).get("hits", [])
            if hits:
                lyrics_url = hits[0]["result"]["url"]
                page = requests.get(lyrics_url)
                soup = BeautifulSoup(page.content, "html.parser")
                lyrics_div = soup.find("div", {"data-lyrics-container": "true"})

                if lyrics_div:
                    return lyrics_div.get_text(separator="\n").strip()
        return "❌ لیریک یافت نشد."
    except Exception as e:
        logger.error(f"Error fetching lyrics: {e}")
        return "❌ خطا در ارتباط با سرور لیریک."

# ====== هندلر اضافه شدن به گروه ======
async def check_new_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_member = update.chat_member
        user_id = chat_member.from_user.id
        chat_id = chat_member.chat.id

        if chat_member.new_chat_member.status == "member" and not is_sudo(user_id):
            await context.bot.leave_chat(chat_id)
            logger.info(f"❌ ربات توسط کاربر غیرمجاز ({user_id}) اضافه شد و گروه را ترک کرد.")
    except Exception as e:
        logger.error(f"Error in check_new_chat_member: {e}")

# ====== هندلر پیام‌های صوتی ======
async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message = update.message
        file_name = message.audio.file_name or "unknown_song"

        audio_file = await message.audio.get_file()
        await audio_file.download_to_drive("input.mp3")

        demo_file = create_demo("input.mp3")
        os.remove("input.mp3")

        if demo_file:
            keyboard = [[InlineKeyboardButton("🎵 Lyrics", callback_data=f"lyrics:{file_name}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            with open(demo_file, "rb") as voice:
                await message.reply_voice(voice=voice, caption=file_name, reply_markup=reply_markup)
            os.remove(demo_file)
    except Exception as e:
        logger.error(f"Error in handle_audio: {e}")

# ====== هندلر درخواست لیریک ======
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        song_name = query.data.split(":", 1)[1]

        await query.answer()
        lyrics = get_lyrics(song_name)
        await context.bot.send_message(chat_id=query.from_user.id, text=lyrics)
    except Exception as e:
        logger.error(f"Error in handle_callback: {e}")

# ====== دستور /start ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text("🎵 سلام! فایل MP3 بفرست تا دموی آهنگ و لیریک آن را دریافت کنی.")
    except Exception as e:
        logger.error(f"Error in start: {e}")

# ====== ثبت هندلرها ======
application.add_handler(CommandHandler("start", start))
application.add_handler(ChatMemberHandler(check_new_chat_member, ChatMemberHandler.CHAT_MEMBER))
application.add_handler(MessageHandler(filters.AUDIO, handle_audio))
application.add_handler(CallbackQueryHandler(handle_callback))

# ====== راه‌اندازی وب‌سرور ======
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        update = Update.de_json(request.get_json(force=True), application.bot)
        asyncio.create_task(application.process_update(update))
        return "OK", 200
    except Exception as e:
        logger.error(f"Error in webhook: {e}")
        return "Internal Server Error", 500

@app.route('/')
def index():
    return "🎵 Bot is running!", 200

# ====== راه‌اندازی Webhook ======
if __name__ == "__main__":
    async def main():
        await application.bot.set_webhook(url=WEBHOOK_URL)
        logger.info("✅ Webhook تنظیم شد.")
        port = int(os.environ.get("PORT", 5000))
        app.run(host="0.0.0.0", port=port)

    asyncio.run(main())
