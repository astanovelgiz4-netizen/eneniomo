import asyncio
import sqlite3
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import *
from aiogram.utils.keyboard import InlineKeyboardBuilder

# =================== SOZLAMALAR ===================
BOT_TOKEN = "7748673962:AAE0KUclQJs6xcwlsFnKvcmhvfl5TpwsxYI"
ADMIN_ID = 6884014716
CHANNEL_USERNAME = "@kinolashamz"  # Majburiy obuna kanali
# ====================================================

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

# ✅ DATABASE (FIX QILINDI)
DB_PATH = os.getenv("DB_PATH", "/tmp/kino.db")
db = sqlite3.connect(DB_PATH)
cur = db.cursor()

# =================== DATABASE ======================
cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS movies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE,
    title TEXT,
    file_id TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS saved (
    user_id INTEGER,
    movie_id INTEGER
)
""")

db.commit()
# ====================================================

# =================== OBUNA TEKSHIRISH ===================
async def check_sub(user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# =================== START ===================
@dp.message(F.text.startswith("/start"))
async def start(msg: Message):
    user_name = msg.from_user.full_name
    text = msg.text

    param = None
    if len(text.split()) > 1:
        param = text.split()[1]

    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Kanalga obuna bo‘lish", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")
    kb.button(text="🔍 Tekshirish", callback_data="check_sub")
    kb.adjust(2)

    if not await check_sub(msg.from_user.id):
        await msg.answer(
            f"Salom {user_name} siz botdan foydalanishingiz uchun avval kanalga obuna bo‘ling❗️",
            reply_markup=kb.as_markup()
        )
        return

    cur.execute(
        "INSERT OR IGNORE INTO users VALUES (?,?)",
        (msg.from_user.id, msg.from_user.username)
    )
    db.commit()

    await bot.send_message(
        ADMIN_ID,
        f"🆕 Yangi foydalanuvchi\n👤 {user_name}\n🆔 {msg.from_user.id}"
    )

    if param and param.isdigit() and len(param) == 3:
        cur.execute("SELECT title, file_id FROM movies WHERE code=?", (param,))
        movie = cur.fetchone()
        if movie:
            await bot.send_video(
                msg.from_user.id,
                movie[1],
                caption=f"🎬 {movie[0]}\n🔢 Kod: {param}"
            )
        else:
            await msg.answer("❌ Bu kodda kino topilmadi")

    kb2 = InlineKeyboardBuilder()
    kb2.button(text="🔍 Inline qidiruv", switch_inline_query_current_chat="")
    kb2.adjust(1)

    await msg.answer(
        f"🎬 Xush kelibsiz! {user_name}",
        reply_markup=kb2.as_markup()
    )

# =================== CHECK ===================
@dp.callback_query(F.data == "check_sub")
async def check_subscription(call: CallbackQuery):
    user_name = call.from_user.full_name

    if await check_sub(call.from_user.id):
        cur.execute(
            "INSERT OR IGNORE INTO users VALUES (?,?)",
            (call.from_user.id, call.from_user.username)
        )
        db.commit()

        await bot.send_message(
            ADMIN_ID,
            f"🆕 Yangi foydalanuvchi\n👤 {user_name}\n🆔 {call.from_user.id}"
        )

        kb2 = InlineKeyboardBuilder()
        kb2.button(text="🔍 Inline qidiruv", switch_inline_query_current_chat="")
        kb2.adjust(1)

        await call.message.edit_text(
            f"🎬 Xush kelibsiz! {user_name}",
            reply_markup=kb2.as_markup()
        )
    else:
        await call.answer("❌ Obuna bo‘lmadingiz", show_alert=True)

# =================== INLINE ===================
@dp.inline_query()
async def inline_search(query: InlineQuery):
    text = query.query

    cur.execute(
        "SELECT id, title, file_id FROM movies WHERE title LIKE ?",
        (f"%{text}%",)
    )
    movies = cur.fetchall()

    results = []
    for m in movies:
        kb = InlineKeyboardBuilder()
        kb.button(text="💾 Saqlash", callback_data=f"save_{m[0]}")

        results.append(
            InlineQueryResultCachedVideo(
                id=str(m[0]),
                video_file_id=m[2],
                title=m[1],
                reply_markup=kb.as_markup()
            )
        )

    await query.answer(results, cache_time=1)

# =================== CODE ===================
@dp.message(F.text.regexp(r"^\d{3}$"))
async def by_code(msg: Message):
    if not await check_sub(msg.from_user.id):
        await msg.answer("❗ Avval obuna bo‘ling")
        return

    cur.execute(
        "SELECT id, title, file_id FROM movies WHERE code=?", (msg.text,)
    )
    movie = cur.fetchone()

    if not movie:
        await msg.answer("❌ Topilmadi")
        return

    kb = InlineKeyboardBuilder()
    kb.button(text="💾 Saqlash", callback_data=f"save_{movie[0]}")

    await bot.send_video(
        msg.chat.id,
        movie[2],
        caption=f"🎬 {movie[1]}",
        reply_markup=kb.as_markup()
    )

# =================== SAVE ===================
@dp.callback_query(F.data.startswith("save_"))
async def save_movie(call: CallbackQuery):
    movie_id = int(call.data.split("_")[1])

    cur.execute(
        "INSERT INTO saved VALUES (?,?)",
        (call.from_user.id, movie_id)
    )
    db.commit()

    await call.answer("💾 Saqlandi")

# =================== RUN ===================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
