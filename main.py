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
START_IMAGE_PATH = "start.jpg"  # Oddiy rasm fayli

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

# =================== DATABASE ======================
DB_PATH = os.getenv("DB_PATH", "/tmp/kino.db")
db = sqlite3.connect(DB_PATH)
cur = db.cursor()

# Foydalanuvchilar
cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT
)
""")
# Kinolar
cur.execute("""
CREATE TABLE IF NOT EXISTS movies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE,
    title TEXT,
    file_id TEXT
)
""")
# Seriallar
cur.execute("""
CREATE TABLE IF NOT EXISTS serials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE,
    title TEXT,
    file_id TEXT
)
""")
# Saqlangan kinolar
cur.execute("""
CREATE TABLE IF NOT EXISTS saved (
    user_id INTEGER,
    movie_id TEXT
)
""")
db.commit()

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
    user_link = f"[{user_name}](tg://user?id={msg.from_user.id})"

    kb = InlineKeyboardBuilder()
    kb.button(text="📢 Obuna bo‘lish", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")
    kb.button(text="✅ Tekshirish", callback_data="check_sub")
    kb.adjust(2)

    if not await check_sub(msg.from_user.id):
        text_msg = f"👋 Assalomu alaykum {user_link}\n🎬 Botdagi filmlarni ko‘rish uchun kanalga obuna bo‘ling!"
        if os.path.exists(START_IMAGE_PATH):
            await msg.answer_photo(START_IMAGE_PATH, caption=text_msg, reply_markup=kb.as_markup(), parse_mode="Markdown")
        else:
            await msg.answer(text_msg, reply_markup=kb.as_markup(), parse_mode="Markdown")
        return

    cur.execute("INSERT OR IGNORE INTO users VALUES (?,?)", (msg.from_user.id, msg.from_user.username))
    db.commit()
    await bot.send_message(ADMIN_ID, f"🆕 Yangi foydalanuvchi\n👤 {user_name}\n🆔 {msg.from_user.id}")

    kb2 = InlineKeyboardBuilder()
    kb2.button(text="🔍 Inline qidiruv", switch_inline_query_current_chat="")
    kb2.adjust(1)
    text_msg = f"👋 Assalomu alaykum {user_link}\nBotdagi barcha filmlarni 🔎 inline qidiruv orqali topishingiz mumkin!"
    await msg.answer(text_msg, reply_markup=kb2.as_markup(), parse_mode="Markdown")

# =================== CHECK SUB ===================
@dp.callback_query(F.data == "check_sub")
async def check_subscription(call: CallbackQuery):
    user_name = call.from_user.full_name
    user_link = f"[{user_name}](tg://user?id={call.from_user.id})"
    if await check_sub(call.from_user.id):
        cur.execute("INSERT OR IGNORE INTO users VALUES (?,?)", (call.from_user.id, call.from_user.username))
        db.commit()
        await bot.send_message(ADMIN_ID, f"🆕 Yangi foydalanuvchi\n👤 {user_name}\n🆔 {call.from_user.id}")

        kb2 = InlineKeyboardBuilder()
        kb2.button(text="🔍 Inline qidiruv", switch_inline_query_current_chat="")
        kb2.adjust(1)
        text_msg = f"👋 Assalomu alaykum {user_link}\nBotdagi barcha filmlarni 🔎 inline qidiruv orqali topishingiz mumkin!"
        await call.message.edit_text(text_msg, reply_markup=kb2.as_markup(), parse_mode="Markdown")
    else:
        await call.answer("❌ Obuna bo‘lmadingiz", show_alert=True)

# =================== INLINE QIDIRUV ===================
@dp.inline_query()
async def inline_search(query: InlineQuery):
    text = query.query
    results = []

    # Kinolar
    cur.execute("SELECT id, title, file_id FROM movies WHERE title LIKE ?", (f"%{text}%",))
    movies = cur.fetchall()
    for m in movies:
        kb = InlineKeyboardBuilder()
        kb.button(text="💾 Saqlash", callback_data=f"save_movie_{m[0]}")
        results.append(InlineQueryResultCachedVideo(id=f"m{m[0]}", video_file_id=m[2], title=m[1], reply_markup=kb.as_markup()))

    # Seriallar
    cur.execute("SELECT id, title, file_id FROM serials WHERE title LIKE ?", (f"%{text}%",))
    serials = cur.fetchall()
    for s in serials:
        kb = InlineKeyboardBuilder()
        kb.button(text="💾 Saqlash", callback_data=f"save_serial_{s[0]}")
        results.append(InlineQueryResultCachedVideo(id=f"s{s[0]}", video_file_id=s[2], title=s[1], reply_markup=kb.as_markup()))

    await query.answer(results, cache_time=1)

# =================== KOD ORQALI KINO ===================
@dp.message(F.text.regexp(r"^\d{3}$"))
async def by_code(msg: Message):
    if not await check_sub(msg.from_user.id):
        await msg.answer("❗ Avval obuna bo‘ling")
        return
    cur.execute("SELECT id, title, file_id FROM movies WHERE code=?", (msg.text,))
    movie = cur.fetchone()
    if not movie:
        await msg.answer("❌ Topilmadi")
        return
    kb = InlineKeyboardBuilder()
    kb.button(text="💾 Saqlash", callback_data=f"save_movie_{movie[0]}")
    await bot.send_video(msg.chat.id, movie[2], caption=f"🎬 {movie[1]}\n🔢 Kod: {msg.text}", reply_markup=kb.as_markup())

# =================== SAVE ===================
@dp.callback_query(F.data.startswith("save_"))
async def save_movie(call: CallbackQuery):
    movie_id = call.data.split("_")[-1]
    cur.execute("INSERT INTO saved VALUES (?,?)", (call.from_user.id, movie_id))
    db.commit()
    await call.answer("💾 Saqlandi")

# =================== ADMIN PANEL ===================
@dp.message(F.from_user.id == ADMIN_ID, F.text == "/admin")
async def admin_panel(msg: Message):
    kb = InlineKeyboardBuilder()
    kb.button(text="🎬 Kino qo‘shish", callback_data="admin_add_movie")
    kb.button(text="🗑 Kino o‘chirish", callback_data="admin_delete_movie")
    kb.button(text="✏️ Kino tahrirlash", callback_data="admin_edit_movie")
    kb.button(text="📃 Kino ro‘yxati", callback_data="admin_list_movies")
    kb.button(text="🎞 Serial qo‘shish", callback_data="admin_add_serial")
    kb.button(text="🗑 Serial o‘chirish", callback_data="admin_delete_serial")
    kb.button(text="✏️ Serial tahrirlash", callback_data="admin_edit_serial")
    kb.button(text="📃 Serial ro‘yxati", callback_data="admin_list_serials")
    kb.button(text="👤 Foydalanuvchi ro‘yxati", callback_data="admin_users")
    kb.button(text="📊 Foydalanuvchi statistikasi", callback_data="admin_stats")
    kb.button(text="📣 Broadcast (inline tugma)", callback_data="admin_broadcast_inline")
    kb.button(text="📢 Broadcast (tugmasiz)", callback_data="admin_broadcast_text")
    kb.adjust(2)
    await msg.answer("Admin panelga xush kelibsiz!", reply_markup=kb.as_markup())

# =================== HOZIRCHA ADMIN HANDLERLAR ===================
# Shu yerga kino/serial qo‘shish, tahrirlash, o‘chirish, ro‘yxat, broadcast handlerlarini qo‘shish kerak.
# Barchasi async def handler_name(...) tarzida yoziladi.
# Masalan:
# @dp.callback_query(F.data == "admin_add_movie")
# async def add_movie(call: CallbackQuery):
#     # Handler kodi shu yerda
#     pass

# =================== RUN ===================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
