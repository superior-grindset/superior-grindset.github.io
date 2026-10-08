"""
SUPERIOR GRINDSET BOT — yengil versiya (Railway Free uchun).

Sayt alohida, GitHub Pages'da (hamma uchun ochiq), shuning uchun
bu yerda faqat bot ishlaydi: kam xotira, 24/7 polling.

Kerakli o'zgaruvchilar (Railway → Variables):
    BOT_TOKEN  — BotFather bergan token (MAXFIY)
    SITE_URL   — saytingiz manzili, masalan https://username.github.io/superior-grindset/
"""

import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)

try:  # kompyuterda .env fayli bo'lsa o'qiydi; serverda shart emas
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logging.basicConfig(level=logging.INFO)

# ==========================
# SOZLAMALAR
# ==========================

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise SystemExit("BOT_TOKEN topilmadi. Railway → Variables bo'limiga qo'shing.")

CHANNEL_URL = "https://t.me/superior_grindset"
SITE_URL = os.getenv("SITE_URL", "").strip()

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ==========================
# MENYULAR
# ==========================

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🏋️ Trening")],
        [KeyboardButton(text="🌐 Sayt"), KeyboardButton(text="ℹ️ Kanal haqida")],
    ],
    resize_keyboard=True,
)

training_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💪 Chest"), KeyboardButton(text="🏋️ Back")],
        [KeyboardButton(text="💪 Biceps"), KeyboardButton(text="💪 Triceps")],
        [KeyboardButton(text="🏋️ Shoulders"), KeyboardButton(text="🦵 Legs")],
        [KeyboardButton(text="⬅️ Orqaga")],
    ],
    resize_keyboard=True,
)

# Mushak guruhlari: tugma matni → (sarlavha, kanal posti)
TRAINING = {
    "💪 Chest": ("💪 CHEST MASHQLARI", "https://t.me/superior_grindset/261"),
    "💪 Triceps": ("💪 TRICEPS MASHQLARI", "https://t.me/superior_grindset/265"),
    "🏋️ Back": ("🏋️ BACK MASHQLARI", "https://t.me/superior_grindset/276"),
    "💪 Biceps": ("💪 BICEPS MASHQLARI", "https://t.me/superior_grindset/284"),
    "🦵 Legs": ("🦵 LEGS MASHQLARI", "https://t.me/superior_grindset/289"),
    "🏋️ Shoulders": ("🏋️ SHOULDERS MASHQLARI", "https://t.me/superior_grindset/299"),
}

# ==========================
# HANDLERLAR
# ==========================

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "🏆 SUPERIOR GRINDSET BOT\n\n"
        "Xush kelibsiz!\n\n"
        "Kerakli bo'limni tanlang.",
        reply_markup=main_menu,
    )


@dp.message(F.text == "🏋️ Trening")
async def training(message: Message):
    await message.answer("💪 Qaysi mushak guruhini mashq qilmoqchisiz?", reply_markup=training_menu)


@dp.message(F.text == "ℹ️ Kanal haqida")
async def about(message: Message):
    await message.answer(
        "🏆 SUPERIOR GRINDSET\n\n"
        "Bu bot sizni kanalimizdagi foydali mashqlar videolariga tez va oson olib boradi.\n\n"
        "📢 Telegram kanal:\n" + CHANNEL_URL
    )


@dp.message(F.text == "🌐 Sayt")
@dp.message(Command("sayt"))
async def site(message: Message):
    if not SITE_URL.startswith("https://"):
        await message.answer("🌐 Sayt tez orada ochiladi.")
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="➡️ Saytni ochish", url=SITE_URL)]])
    await message.answer(
        "🌐 SUPERIOR GRINDSET SAYTI\n\n"
        "Mashq videolari, texnika, ovqatlanish va foydali ma'lumotlar — hammasi bir joyda.",
        reply_markup=kb,
    )


@dp.message(F.text == "⬅️ Orqaga")
async def back(message: Message):
    await message.answer("🏠 Asosiy menyu", reply_markup=main_menu)


@dp.message(F.text.in_(TRAINING.keys()))
async def muscle(message: Message):
    title, url = TRAINING[message.text]
    await message.answer(f"{title}\n\n🎥 Video:\n{url}")


@dp.message(Command("myid"))
async def my_id(message: Message):
    await message.answer(f"Sizning Telegram ID: {message.from_user.id}")


@dp.message()
async def unknown(message: Message):
    await message.answer("❗ Iltimos, menyudagi tugmalardan foydalaning.")

# ==========================
# MAIN
# ==========================

async def main():
    me = await bot.get_me()
    logging.info("Bot ishga tushdi: @%s", me.username)
    # Eski (kompyuterdagi) bot qoldirgan xabarlarni tashlab, toza boshlaydi
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
