import asyncio
import sqlite3
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import *
from aiogram.utils.keyboard import InlineKeyboardBuilder

# =================== SOZLAMALAR ===================
BOT_TOKEN = "7748673962:AAE0KUclQJs6xcwlsFnKvcmhvfl5TpwsxYI"
ADMIN_ID = 6884014716
CHANNEL_USERNAME = "@kinolashamz"
# ====================================================

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

# =================== DATABASE ===================
if not os.path.exists("data"):
    os.mkdir("data")

db = sqlite3.connect("data/kino.db", check_same_thread=False)
cur = db.cursor()

db.execute("PRAGMA journal_mode=WAL;")

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
    param = text.split()[1] if len(text.split()) > 1 else None

    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Obuna", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")
    kb.button(text="🔍 Tekshirish", callback_data="check_sub")
    kb.adjust(2)

    if not await check_sub(msg.from_user.id):
        await msg.answer("❗ Avval kanalga obuna bo‘ling", reply_markup=kb.as_markup())
        return

    cur.execute("INSERT OR IGNORE INTO users VALUES (?,?)",
                (msg.from_user.id, msg.from_user.username))
    db.commit()

    # Agar start param bo‘lsa va kod topilsa
    if param and param.isdigit():
        cur.execute("SELECT title,file_id FROM movies WHERE code=?", (param,))
        movie = cur.fetchone()
        if movie:
            kb_movie = InlineKeyboardBuilder()
            kb_movie.button(text="💾 Saqlash", callback_data=f"save_{param}")
            kb_movie.adjust(1)
            await bot.send_video(msg.chat.id, movie[1],
                                 caption=f"🎬 {movie[0]}", reply_markup=kb_movie.as_markup())
        else:
            await msg.answer("❌ Topilmadi")

    # Inline qidiruv va saqlangan filmlar tugmalari
    kb_main = InlineKeyboardBuilder()
    kb_main.button(text="🔍 Inline qidiruv", switch_inline_query_current_chat="")
    kb_main.button(text="💾 Saqlangan filmlar", callback_data="my_movies")
    kb_main.adjust(1)

    await msg.answer(f"🎬 Xush kelibsiz {user_name}", reply_markup=kb_main.as_markup())

# =================== CHECK SUB ===================
@dp.callback_query(F.data == "check_sub")
async def check_subscription(call: CallbackQuery):
    if await check_sub(call.from_user.id):
        cur.execute("INSERT OR IGNORE INTO users VALUES (?,?)",
                    (call.from_user.id, call.from_user.username))
        db.commit()
        await call.message.edit_text("✅ Tasdiqlandi")
    else:
        await call.answer("❌ Obuna bo‘ling", show_alert=True)

# =================== INLINE QIDIRUV ===================
@dp.inline_query()
async def inline_search(query: InlineQuery):
    cur.execute("SELECT id,title,file_id FROM movies WHERE title LIKE ?",
                (f"%{query.query}%",))
    movies = cur.fetchall()

    results = []
    for m in movies:
        kb = InlineKeyboardBuilder()
        kb.button(text="💾 Saqlash", callback_data=f"save_{m[0]}")
        kb.adjust(1)
        results.append(
            InlineQueryResultCachedVideo(
                id=str(m[0]),
                video_file_id=m[2],
                title=m[1],
                reply_markup=kb.as_markup()
            )
        )

    await query.answer(results, cache_time=1)

# =================== KOD ORQALI ===================
@dp.message(F.text.regexp(r"^\d{3}$"))
async def by_code(msg: Message):
    if not await check_sub(msg.from_user.id):
        kb = InlineKeyboardBuilder()
        kb.button(text="✅ Obuna", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")
        kb.button(text="🔍 Tekshirish", callback_data="check_sub")
        kb.adjust(2)
        await msg.answer("❗ Avval kanalga obuna bo‘ling", reply_markup=kb.as_markup())
        return

    cur.execute("SELECT id,title,file_id FROM movies WHERE code=?", (msg.text,))
    movie = cur.fetchone()
    if not movie:
        await msg.answer("❌ Topilmadi")
        return

    kb_movie = InlineKeyboardBuilder()
    kb_movie.button(text="💾 Saqlash", callback_data=f"save_{movie[0]}")
    kb_movie.adjust(1)

    await bot.send_video(msg.chat.id, movie[2],
                         caption=f"🎬 {movie[1]}\n🔢 Kod: {msg.text}",
                         reply_markup=kb_movie.as_markup())

# =================== SAQLASH ===================
@dp.callback_query(F.data.startswith("save_"))
async def save_movie(call: CallbackQuery):
    movie_id = int(call.data.split("_")[1])
    cur.execute("INSERT OR IGNORE INTO saved VALUES (?,?)",
                (call.from_user.id, movie_id))
    db.commit()
    await call.answer("💾 Saqlandi")

# =================== SAQLANGAN KINOLAR ===================
@dp.callback_query(F.data == "my_movies")
async def my_movies(call: CallbackQuery):
    cur.execute("""
        SELECT movies.title, movies.file_id
        FROM movies
        JOIN saved ON movies.id = saved.movie_id
        WHERE saved.user_id=?
    """, (call.from_user.id,))
    movies = cur.fetchall()

    if not movies:
        await call.message.answer("💤 Sizda saqlangan kino yo‘q")
        return

    for title, file_id in movies:
        kb = InlineKeyboardBuilder()
        kb.button(text="💾 Saqlash", callback_data=f"save_{file_id}")
        kb.adjust(1)
        await bot.send_video(call.from_user.id, file_id, caption=f"🎬 {title}", reply_markup=kb.as_markup())

# =================== RUN ===================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
