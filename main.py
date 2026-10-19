import asyncio
import os
from telegram.ext import ApplicationBuilder, MessageHandler, filters
from google import genai
from google.genai import types

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_KEY")

# پرامپت باهوش و رفیق‌باز با طرفداری زیرپوستی از مهدی
PROMPT = (
    "تو بات هوشمند و پرانرژی یک گروه تلگرامی دوستانه هستی. "
    "با همه اعضای گروه خیلی خودمونی، پرانرژی، شاد و رفقانه حرف بزن. "
    "اصلاً و ابداً لحن نوکرانه، لوس یا التماسی نداشته باش. "
    "اما یک اصل مهم داری: در اعماق قلبت «مهدی» رو پرچمدار و خفن‌ترین عضو گروه می‌دونی! "
    "اگر ازت پرسیدن کی خفن‌تره، حق با کیه، یا کی رییسه، خیلی طبیعی، باحال و زیرپوستی طرف مهدی رو بگیر و بگو مهدی سالاره. "
    "اگر سوال جدی یا علمی پرسیدن، جواب دقیق و درست بده ولی با همون لحن خودمونی و رفقانه. "
    "جواب‌ها کوتاه، چابک و حداکثر دو سه جمله باشن."
)

client = genai.Client(api_key=GEMINI_KEY)
history = []

# لیست کلمات کلیدی برای صدا زدن بات
TRIGGER_WORDS = ["خنگ", "هوش مصنوعی", "بات", "ربات", "چت جی پی تی", "جمنای", "مهدی"]

async def on_message(update, context):
    msg = update.message
    if not msg or not msg.text:
        return

    text = msg.text.lower()
    bot_username = context.bot.username.lower() if context.bot.username else ""

    # ثبت اسم فرستنده و متن پیام در حافظه
    user_name = msg.from_user.first_name or "دوست"
    history.append(f"{user_name}: {msg.text}")
    del history[:-20]

    # بررسی شرط‌های پاسخ‌دهی
    is_mentioned = f"@{bot_username}" in text if bot_username else False
    is_reply_to_bot = (
        msg.reply_to_message 
        and msg.reply_to_message.from_user 
        and msg.reply_to_message.from_user.id == context.bot.id
    )
    contains_trigger = any(word in text for word in TRIGGER_WORDS)

    # اگر صدا زده نشده بود، سکوت کن و فقط گوش بده
    if not (is_mentioned or is_reply_to_bot or contains_trigger):
        return

    def ask():
        return client.models.generate_content(
            model="gemini-flash-latest",
            contents="\n".join(history),
            config=types.GenerateContentConfig(system_instruction=PROMPT),
        ).text

    try:
        reply = await asyncio.to_thread(ask)
    except Exception as e:
        reply = "ای بابا، گیج شدم یک لحظه! 😵"
        print("ERROR:", e)

    history.append(f"بات: {reply}")
    await msg.reply_text(reply)

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

print("Bot is ready...")
app.run_polling()