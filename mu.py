import os
import requests
from flask import Flask, request
from pydub import AudioSegment
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes

# ====== تنظیمات ======
BOT_TOKEN = "7830811506:AAHviqGsjxf1S57-W46F5bu9Rh9kuZIQ-fY"  # یییتوکن ربات
GENIUS_API_TOKEN = "1k3ljpOFJhSQs52wnj8MaAnfFqVfLGOzBXUhBakw7aD1SAvQsVqih4RK8ds8CLNx"  # توکن API از Genius
SUDO_USERS = [5668163693, 987654321]  # آیدی عددی سودوها
WEBHOOK_URL = "https://music-xirn.onrender.com/webhook"  # دامنه Render شما

# ====== ایجاد Flask App ======
app = Flask(__name__)
application = ApplicationBuilder().token(BOT_TOKEN).build()

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
        print(f"Error creating demo: {e}")
        return None

# ====== دریافت لیریک از Genius ======
def get_lyrics(song_name):
    try:
        headers = {"Authorization": f"Bearer {GENIUS_API_TOKEN}"}
        search_url = "https://api.genius.com/search"
        response = requests.get(search_url, headers=headers, params={"q": song_name})

        if response.status_code == 200:
            hits = response.json()["response"]["hits"]
            if hits:
                lyrics_url = hits[0]["result"]["url"]
                return f"🎵 لیریک آهنگ:\n{lyrics_url}"
        return "❌ لیریک یافت نشد."
    except Exception as e:
        print(f"Error fetching lyrics: {e}")
        return "❌ خطا در ارتباط با سرور لیریک."

# ====== مدیریت Webhook ======
@app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put(update)
    return "OK", 200

@app.route('/')
def index():
    return "Bot is running!", 200

# ====== مدیریت فایل MP3 ======
@application.message_handler(filters.AUDIO)
async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    file_name = message.audio.file_name or "unknown_song"

    # دانلود فایل MP3
    audio_file = await message.audio.get_file()
    await audio_file.download_to_drive("input.mp3")

    # تولید دمو
    demo_file = create_demo("input.mp3")
    os.remove("input.mp3")

    if demo_file:
        with open(demo_file, "rb") as voice:
            await message.reply_voice(voice=voice, caption=file_name)
        os.remove(demo_file)

# ====== دستور /start ======
@application.command_handler("start")
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎵 سلام! فایل MP3 بفرست تا دموی آهنگ و لیریک آن را دریافت کنی.")

# ====== اجرای Flask ======
if __name__ == "__main__":
    application.bot.set_webhook(url=WEBHOOK_URL)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
