import os, json, re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from yt_dlp import YoutubeDL

DATA_FILE = "data.json"
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({"movies": [], "series": [], "songs": []}, f, ensure_ascii=False, indent=2)

def load_data():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

# --- يوتيوب ---
def search_youtube(query, max_results=5):
    ydl_opts = {"quiet": True, "skip_download": True, "extract_flat": True}
    with YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
        return result.get('entries', [])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎬 افلام", callback_data="movies"),
         InlineKeyboardButton("📺 مسلسلات", callback_data="series")],
        [InlineKeyboardButton("🎵 اغاني - بحث يوتيوب", callback_data="songs")],
        [InlineKeyboardButton("🔍 ابحث في يوتيوب", callback_data="yt_search")]
    ]
    await update.message.reply_text(
        "🔥 **VTR Bot + YouTube** 🔥\nاختار قسم او ابعت اسم اي اغنية/فيلم وهيجبهولك من يوتيوب:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def handle_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.message.text
    await update.message.reply_text(f"🔍 ببحث عن: {q} في يوتيوب...")
    results = search_youtube(q, 5)
    if not results:
        await update.message.reply_text("ملقتش حاجة 😢")
        return
    keyboard = []
    for r in results:
        title = r.get('title')[:40]
        vid = r.get('id')
        url = f"https://www.youtube.com/watch?v={vid}"
        keyboard.append([InlineKeyboardButton(f"▶️ {title}", url=url)])
        keyboard.append([InlineKeyboardButton(f"🎧 شغل {title[:20]} هنا", callback_data=f"play_{vid}")])

    await update.message.reply_text(
        f"نتائج يوتيوب لـ: {q}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def play_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    vid = query.data.replace("play_", "")
    url = f"https://www.youtube.com/watch?v={vid}"
    await query.edit_message_text(f"⏬ بحمل: {url}")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": f"{vid}.%(ext)s",
        "quiet": True,
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}]
    }
    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        mp3_file = f"{vid}.mp3"
        if os.path.exists(mp3_file):
            await context.bot.send_audio(chat_id=query.message.chat_id, audio=open(mp3_file, 'rb'), title=vid)
            os.remove(mp3_file)
    except Exception as e:
        await context.bot.send_message(chat_id=query.message.chat_id, text=f"حصل ايرور: {e}\nشغله مباشر: {url}")

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "yt_search":
        await query.message.reply_text("ابعت اسم اي اغنية او فيلم وانا هجيبهولك من يوتيوب 🎵")
        return
    # اقسام قديمة
    data = load_data()
    items = data.get(query.data, [])
    text = f"📂 {query.data}: {len(items)} عنصر\n\n" + "\n".join([f"{i+1}. {x}" for i, x in enumerate(items[:20])])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ رجوع", callback_data="back")]]))

async def back_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await start(query, context)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN")
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(back_handler, pattern="back"))
app.add_handler(CallbackQueryHandler(play_audio, pattern="^play_"))
app.add_handler(CallbackQueryHandler(buttons, pattern="^(movies|series|songs|yt_search)$"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search))

print("VTR + YouTube Running...")
app.run_polling()
