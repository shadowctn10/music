cimport os
import requests
from flask import Flask, request
from pydub import AudioSegment
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ChatMemberHandler,
    ContextTypes, filters
)

# ====== تنظیمات ======
BOT_TOKEN = "7830811506:AAHviqGsjxf1S57-W46F5bu9Rh9kuZIQ-fY"  # یییتوکن ربات
GENIUS_API_TOKEN = "1k3ljpOFJhSQs52wnj8MaAnfFqVfLGOzBXUhBakw7aD1SAvQsVqih4RK8ds8CLNx"  # توکن API از Genius
SUDO_USERS = [5668163693, 987654321]  # آیدی عددی سودوها
WEBHOOK_URL = "https://music-xirn.onrender.com/webhook"  # دامنه Render شما


# ====== راه‌اندازی Flask برای cوب‌سرور ======
app = Flask(__name__)

# ====== ایجاد Application تلگرام ======
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
        response = requests.get("https://api.genius.com/search", headers=headers, params={"q": song_name})

        if response.status_code == 200:
            hits = response.json()["response"]["hits"]
            if hits:
                lyrics_url = hits[0]["result"]["url"]

                # استخراج متن لیریک از صفحه HTML
                page = requests.get(lyrics_url)
                soup = BeautifulSoup(page.content, "html.parser")
                lyrics_div = soup.find("div", {"data-lyrics-container": "true"})

                if lyrics_div:
                    lyrics = lyrics_div.get_text(separator="\n").strip()
                    return lyrics
        return "❌ لیریک یافت نشد."
    except Exception as e:
        print(f"Error fetching lyrics: {e}")
        return "❌ خطا در ارتباط با سرور لیریک."

# ====== هندلر اضافه شدن به گروه ======
async def check_new_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_member = update.chat_member
    user_id = chat_member.from_user.id
    chat_id = chat_member.chat.id

    if chat_member.new_chat_member.status == "member" and not is_sudo(user_id):
        await context.bot.leave_chat(chat_id)
        print(f"❌ ربات توسط کاربر غیرمجاز ({user_id}) اضافه شد و گروه را ترک کرد.")

# ====== هندلر پیام‌های صوتی ======
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
        keyboard = [[InlineKeyboardButton("🎵 Lyrics", callback_data=f"lyrics:{file_name}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        with open(demo_file, "rb") as voice:
            await message.reply_voice(voice=voice, caption=file_name, reply_markup=reply_markup)
        os.remove(demo_file)

# ====== هندلر درخواست لیریک ======
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    song_name = query.data.split(":", 1)[1]

    await query.answer()
    lyrics = get_lyrics(song_name)
    await context.bot.send_message(chat_id=query.from_user.id, text=lyrics)

# ====== دستور /start ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎵 سلام! فایل MP3 بفرست تا دموی آهنگ و لیریک آن را دریافت کنی.")

# ====== ثبت هندلرها ======
application.add_handler(CommandHandler("start", start))
application.add_handler(ChatMemberHandler(check_new_chat_member, ChatMemberHandler.CHAT_MEMBER))
application.add_handler(MessageHandler(filters.AUDIO, handle_audio))
application.add_handler(CallbackQueryHandler(handle_callback))

# ====== راه‌اندازی وب‌سرور ======
@app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put(update)
    return "OK", 200

@app.route('/')
def index():
    return "🎵 Bot is running!", 200

if __name__ == "__main__":
    application.bot.set_webhook(url=WEBHOOK_URL)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
