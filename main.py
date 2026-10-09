"""
SUPERIOR GRINDSET BOT — yengil versiya (Railway Free uchun).

Sayt alohida, GitHub Pages'da (hamma uchun ochiq), shuning uchun
bu yerda faqat bot ishlaydi: kam xotira, 24/7 polling.

YANGI: kanalga avtomatik post.
    Bot har daqiqada saytdagi data.json ni o'qiydi. Postning "date" + "time"
    (Toshkent vaqti) kelganda uni kanalga yuboradi. Sayt ham shu vaqtgacha
    postni yashiradi — bitta data.json yuklansa, ikkalasi birga ishlaydi.
    Har kuni 20:00 da ertangi post yo'q bo'lsa, egasiga eslatma yuboradi.

Kerakli o'zgaruvchilar (Railway → Variables):
    BOT_TOKEN  — BotFather bergan token (MAXFIY)
    SITE_URL   — https://superior-grindset.github.io
    CHANNEL_ID — (ixtiyoriy) standart: @superior_grindset
Bot kanalda ADMIN bo'lishi va "Post joylash" huquqi bo'lishi kerak.
"""

import asyncio
import html
import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone

import aiohttp
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    LinkPreviewOptions,
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
CHANNEL_ID = os.getenv("CHANNEL_ID", "@superior_grindset").strip()
SITE_URL = os.getenv("SITE_URL", "").strip()
OWNER_IDS = {1015734340}

TZ = timezone(timedelta(hours=5))   # Toshkent (yozgi vaqt yo'q)
DEFAULT_TIME = "09:00"              # post vaqti ko'rsatilmasa
WINDOW_MIN = 15                     # vaqt kelgandan keyin shu daqiqa ichida yuboradi
REMIND_HOUR = 20                    # ertangi post yo'qligi haqida eslatma soati
POSTED_FILE = "posted.json"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ==========================
# MENYULAR
# ==========================

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🏋️ Trening")],
        [KeyboardButton(text="🌐 Sayt"), KeyboardButton(text="ℹ️ Kanal haqida")],
        [KeyboardButton(text="✍️ Savol berish")],
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
# KANALGA AVTOMATIK POST
# ==========================

def load_posted() -> set:
    try:
        with open(POSTED_FILE, encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()


def save_posted() -> None:
    try:
        with open(POSTED_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(posted), f)
    except Exception:
        logging.exception("posted.json yozilmadi")


posted = load_posted()

# ==========================
# BOT STATISTIKASI
# ==========================
# users.json: {"<id>": {"name", "username", "first": "YYYY-MM-DD", "last": "YYYY-MM-DD"}}
# stats.json: {"questions": {"YYYY-MM-DD": n}}
# Eslatma: Railway bepulda bot qayta deploy qilinsa bu fayllar o'chishi mumkin.
USERS_FILE = "users.json"
STATS_FILE = "stats.json"


def _load(path: str, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save(path: str, data) -> None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception:
        logging.exception("%s yozilmadi", path)


users = _load(USERS_FILE, {})
stats = _load(STATS_FILE, {"questions": {}})


def today() -> str:
    return datetime.now(TZ).date().isoformat()


async def track_user(handler, event, data):
    """Har bir shaxsiy xabarda foydalanuvchini eslab qoladi; yangi bo'lsa egaga xabar beradi."""
    u = getattr(event, "from_user", None)
    if u and not u.is_bot and event.chat.type == "private" and u.id not in OWNER_IDS:
        key = str(u.id)
        d = today()
        rec = users.get(key)
        if rec is None:
            users[key] = {"name": u.full_name, "username": u.username or "", "first": d, "last": d}
            _save(USERS_FILE, users)
            uname = f" (@{u.username})" if u.username else ""
            await notify_owners(f"👋 Yangi foydalanuvchi: {u.full_name}{uname}\nJami: {len(users)} ta")
        elif rec.get("last") != d:
            rec["last"] = d
            rec["name"] = u.full_name
            rec["username"] = u.username or ""
            _save(USERS_FILE, users)
    return await handler(event, data)


dp.message.outer_middleware(track_user)


def site_base() -> str:
    return SITE_URL.rstrip("/") if SITE_URL.startswith("https://") else ""


def when_of(p: dict):
    try:
        d = datetime.strptime(p["date"] + " " + (p.get("time") or DEFAULT_TIME), "%Y-%m-%d %H:%M")
        return d.replace(tzinfo=TZ)
    except Exception:
        return None


async def fetch_posts() -> list:
    base = site_base()
    if not base:
        return []
    url = f"{base}/data.json?t={int(time.time())}"
    async with aiohttp.ClientSession() as s:
        async with s.get(url, timeout=aiohttp.ClientTimeout(total=20)) as r:
            r.raise_for_status()
            data = await r.json(content_type=None)
    return [p for p in data.get("posts", []) if p.get("id") and p.get("date")]


def channel_text(p: dict) -> str:
    """Kanal uchun qisqa matn: "tg" maydoni (1-qator qalin) yoki sarlavha + matn."""
    raw = (p.get("tg") or "").strip()
    if raw:
        first, _, rest = raw.partition("\n")
        text = f"<b>{html.escape(first, quote=False)}</b>" + (("\n" + html.escape(rest, quote=False)) if rest else "")
    else:
        text = f"<b>{html.escape(p.get('title', ''), quote=False)}</b>\n\n{html.escape(p.get('body', ''), quote=False)}"
    base = site_base()
    if base:
        text += f'\n\n👉 <a href="{base}/#/post/{p["id"]}">To\'liq maqola saytda</a>'
    return text


async def send_post(chat_id, p: dict):
    return await bot.send_message(
        chat_id, channel_text(p), parse_mode="HTML",
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )


async def notify_owners(text: str) -> None:
    for uid in OWNER_IDS:
        try:
            await bot.send_message(uid, text)
        except Exception:
            logging.warning("Egaga xabar yuborilmadi: %s", uid)


async def scheduler() -> None:
    last_remind = None
    while True:
        try:
            now = datetime.now(TZ)
            posts = await fetch_posts()
            for p in posts:
                w = when_of(p)
                if p["id"] in posted or not w:
                    continue
                if w <= now <= w + timedelta(minutes=WINDOW_MIN):
                    try:
                        await send_post(CHANNEL_ID, p)
                        posted.add(p["id"])
                        save_posted()
                        await notify_owners(f"✅ Kanalga chiqdi: {p.get('title', p['id'])}")
                    except Exception as e:
                        logging.exception("Kanalga yuborilmadi")
                        await notify_owners(f"❗ Kanalga yuborilmadi: {p.get('title', p['id'])}\n{e}\n\nBot kanalda admin ekanini tekshiring.")
            if now.hour == REMIND_HOUR and last_remind != now.date():
                last_remind = now.date()
                tomorrow = (now + timedelta(days=1)).date().isoformat()
                if not any(p["date"] == tomorrow for p in posts):
                    await notify_owners("⏰ Ertaga kanal uchun post yo'q.\nClaude bilan yangi maqola tayyorlang va data.json ni GitHub'ga yuklang.")
        except Exception:
            logging.exception("Rejalashtiruvchida xato")
        await asyncio.sleep(60)

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


@dp.message(F.text == "✍️ Savol berish")
async def ask_hint(message: Message):
    await message.answer("✍️ Savolingizni shu yerga yozing (matn, rasm yoki ovozli xabar). Javobni shu botda olasiz.")


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


# ---- faqat egasi uchun ----

def is_owner(message: Message) -> bool:
    return bool(message.from_user) and message.from_user.id in OWNER_IDS


@dp.message(Command("navbat"))
async def queue(message: Message):
    if not is_owner(message):
        return
    now = datetime.now(TZ)
    try:
        posts = await fetch_posts()
    except Exception as e:
        await message.answer(f"❗ data.json o'qilmadi: {e}")
        return
    soon = sorted((p for p in posts if (when_of(p) or now) > now), key=when_of)
    if not soon:
        await message.answer("📭 Navbatda post yo'q.")
        return
    lines = [f"• {when_of(p):%d.%m %H:%M} — {p.get('title', p['id'])}  (/korish {p['id']})" for p in soon]
    await message.answer("🗓 Navbatdagi postlar:\n\n" + "\n".join(lines))


async def find_post(message: Message, command: CommandObject):
    pid = (command.args or "").strip()
    if not pid:
        await message.answer("Post id ni yozing, masalan: /korish uglevod")
        return None
    try:
        posts = await fetch_posts()
    except Exception as e:
        await message.answer(f"❗ data.json o'qilmadi: {e}")
        return None
    p = next((x for x in posts if x["id"] == pid), None)
    if not p:
        await message.answer("Bunday post topilmadi.")
    return p


@dp.message(Command("korish"))
async def preview(message: Message, command: CommandObject):
    if not is_owner(message):
        return
    p = await find_post(message, command)
    if p:
        await send_post(message.chat.id, p)


@dp.message(Command("yubor"))
async def publish_now(message: Message, command: CommandObject):
    if not is_owner(message):
        return
    p = await find_post(message, command)
    if not p:
        return
    try:
        await send_post(CHANNEL_ID, p)
        posted.add(p["id"])
        save_posted()
        await message.answer("✅ Kanalga yuborildi.")
    except Exception as e:
        await message.answer(f"❗ Yuborilmadi: {e}\nBot kanalda admin ekanini tekshiring.")


@dp.message(Command("stat"))
async def stat(message: Message):
    if not is_owner(message):
        return
    d = today()
    week_ago = (datetime.now(TZ) - timedelta(days=6)).date().isoformat()
    total = len(users)
    new_today = sum(1 for r in users.values() if r.get("first") == d)
    new_week = sum(1 for r in users.values() if r.get("first", "") >= week_ago)
    active_today = sum(1 for r in users.values() if r.get("last") == d)
    active_week = sum(1 for r in users.values() if r.get("last", "") >= week_ago)
    q = stats.get("questions", {})
    q_today = q.get(d, 0)
    q_week = sum(v for k, v in q.items() if k >= week_ago)
    q_all = sum(q.values())
    last = sorted(users.values(), key=lambda r: r.get("first", ""), reverse=True)[:5]
    last_lines = "\n".join(
        f"• {r.get('name', '?')}" + (f" (@{r['username']})" if r.get("username") else "") + f" — {r.get('first', '')}"
        for r in last
    ) or "—"
    await message.answer(
        "📊 BOT STATISTIKASI\n\n"
        f"👥 Jami foydalanuvchi: {total}\n"
        f"🆕 Yangi: bugun {new_today} · 7 kunda {new_week}\n"
        f"🔥 Faol: bugun {active_today} · 7 kunda {active_week}\n"
        f"❓ Savollar: bugun {q_today} · 7 kunda {q_week} · jami {q_all}\n\n"
        f"Oxirgi yangi foydalanuvchilar:\n{last_lines}\n\n"
        f"🌐 Sayt statistikasi: https://superiorgrindset.goatcounter.com"
    )


# ---- SAVOLLAR: obunachi → egasi, egasi "Reply" qilsa → obunachiga ----

ASK_TAG = "🆔 "


@dp.message(F.reply_to_message, F.from_user.id.in_(list(OWNER_IDS)), F.chat.type == "private")
async def owner_reply(message: Message):
    src = message.reply_to_message
    text = (src.text or src.caption or "")
    uid = None
    for line in text.splitlines():
        if line.startswith(ASK_TAG):
            try:
                uid = int(line[len(ASK_TAG):].strip())
            except ValueError:
                pass
    if not uid:
        await message.answer("Javob berish uchun savol xabariga (🆔 qatori bor xabarga) Reply qiling.")
        return
    try:
        await bot.send_message(uid, "💬 SUPERIOR GRINDSET javobi:")
        await message.copy_to(uid)
        await message.answer("✅ Javob yuborildi.")
    except Exception as e:
        await message.answer(f"❗ Yuborilmadi: {e}")


@dp.message(F.chat.type == "private")
async def question(message: Message):
    u = message.from_user
    if u and u.id in OWNER_IDS:
        await message.answer("ℹ️ Obunachiga javob berish uchun uning savoliga Reply qiling.")
        return
    name = u.full_name if u else "Noma'lum"
    uname = f" (@{u.username})" if u and u.username else ""
    head = f"❓ Yangi savol\n👤 {name}{uname}\n{ASK_TAG}{u.id}"
    sent = 0
    for oid in OWNER_IDS:
        try:
            if message.text:
                await bot.send_message(oid, f"{head}\n\n{message.text}")
            else:  # rasm, video, ovozli xabar: avval sarlavha, keyin o'zi
                h = await bot.send_message(oid, head)
                await message.copy_to(oid, reply_to_message_id=h.message_id)
            sent += 1
        except Exception:
            logging.exception("Savol egaga yuborilmadi")
    if sent:
        d = today()
        stats.setdefault("questions", {})[d] = stats.get("questions", {}).get(d, 0) + 1
        _save(STATS_FILE, stats)
        await message.answer("✅ Savolingiz qabul qilindi. Tez orada javob beramiz.", reply_markup=main_menu)
    else:
        await message.answer("❗ Hozir savolni yuborib bo'lmadi, birozdan keyin qayta urinib ko'ring.")


@dp.message()
async def unknown(message: Message):
    pass  # guruh/kanaldagi boshqa xabarlarga javob bermaydi

# ==========================
# MAIN
# ==========================

async def main():
    me = await bot.get_me()
    logging.info("Bot ishga tushdi: @%s", me.username)
    # Eski (kompyuterdagi) bot qoldirgan xabarlarni tashlab, toza boshlaydi
    await bot.delete_webhook(drop_pending_updates=True)
    sched = asyncio.create_task(scheduler())  # havola saqlanadi, aks holda GC o'chirishi mumkin
    try:
        await dp.start_polling(bot)
    finally:
        sched.cancel()


if __name__ == "__main__":
    asyncio.run(main())
