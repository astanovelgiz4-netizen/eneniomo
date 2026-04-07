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
START_IMAGE_PATH = "start.jpg"

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

# =================== ADMIN VAQTINCHALIK ===================
dp.data = {}

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
        text_msg = f"""👋 Assalomu alaykum {user_link}
🎬 Botdagi eng zo‘r filmlarni tomosha qilish uchun faqat 1ta rasmiy kanalimizga obuna bo‘lishingiz kerak!
💡 Kanalga obuna bo‘lgach, siz barcha filmlarga kirish huquqiga ega bo‘lasiz!"""
        
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
    text_msg = f"""👋 Assalomu alaykum {user_link}
🎬 Botdagi barcha filmlarni 🔎 inline qidiruvi va 📟 kod orqali topishingiz mumkin!"""
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
        text_msg = f"""👋 Assalomu alaykum {user_link}
Botdagi barcha filmlarni 🔎 inline qidiruv orqali topishingiz mumkin!"""
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
@dp.message(F.text.regexp(r"^\d{1,15}$"))
async def by_code(msg: Message):
    if not await check_sub(msg.from_user.id):
        await msg.answer("❗ Avval obuna bo‘ling")
        return
    cur.execute("SELECT id, title, file_id FROM movies WHERE code=?", (msg.text,))
    movie = cur.fetchone()
    if movie:
        kb = InlineKeyboardBuilder()
        kb.button(text="💾 Saqlash", callback_data=f"save_movie_{movie[0]}")
        await bot.send_video(msg.chat.id, movie[2], caption=f"🎬 {movie[1]}\n🔢 Kod: {msg.text}", reply_markup=kb.as_markup())
        return
    cur.execute("SELECT id, title, file_id FROM serials WHERE code=?", (msg.text,))
    serial = cur.fetchone()
    if serial:
        kb = InlineKeyboardBuilder()
        kb.button(text="💾 Saqlash", callback_data=f"save_serial_{serial[0]}")
        await bot.send_video(msg.chat.id, serial[2], caption=f"🎞 {serial[1]}\n🔢 Kod: {msg.text}", reply_markup=kb.as_markup())
        return
    await msg.answer("❌ Topilmadi")

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

# =================== ADMIN ADD/DELETE/EDIT ===================
@dp.callback_query(F.data.startswith("admin_add_"))
async def admin_add(call: CallbackQuery):
    add_type = "movie" if call.data.endswith("movie") else "serial"
    dp.data["add_type"] = add_type
    await call.message.answer(f"🎬 {add_type.capitalize()} qo‘shish. Video yuboring va caption: kod|Nom")
    await call.answer()

@dp.callback_query(F.data.startswith("admin_delete_"))
async def admin_delete(call: CallbackQuery):
    del_type = "movie" if call.data.endswith("movie") else "serial"
    dp.data["delete_type"] = del_type
    await call.message.answer(f"🗑 {del_type.capitalize()} o‘chirish uchun kod yuboring:")
    await call.answer()

@dp.callback_query(F.data.startswith("admin_edit_"))
async def admin_edit(call: CallbackQuery):
    edit_type = "movie" if call.data.endswith("movie") else "serial"
    dp.data["edit_type"] = edit_type
    await call.message.answer(f"✏️ {edit_type.capitalize()} tahrirlash uchun: Kod|Yangi nom")
    await call.answer()

# Video qabul qilish
@dp.message(F.content_type == "video")
async def handle_video(msg: Message):
    add_type = dp.data.get("add_type")
    if not add_type:
        return
    if not msg.caption or "|" not in msg.caption:
        await msg.answer("❌ Format noto‘g‘ri. Format: kod|Nom")
        return
    code, title = [p.strip() for p in msg.caption.split("|", 1)]
    table = "movies" if add_type == "movie" else "serials"
    try:
        cur.execute(f"INSERT INTO {table} (code,title,file_id) VALUES (?,?,?)", (code, title, msg.video.file_id))
        db.commit()
        await msg.answer(f"✅ {title} qo‘shildi!")
    except sqlite3.IntegrityError:
        await msg.answer("❌ Bu kod mavjud!")
    dp.data["add_type"] = None

# Delete handle
@dp.message(F.from_user.id == ADMIN_ID)
async def handle_delete(msg: Message):
    delete_type = dp.data.get("delete_type")
    if not delete_type:
        return
    code = msg.text.strip()
    table = "movies" if delete_type == "movie" else "serials"
    cur.execute(f"DELETE FROM {table} WHERE code=?", (code,))
    db.commit()
    await msg.answer(f"✅ {code} kodi bilan {delete_type} o‘chirildi!")
    dp.data["delete_type"] = None

# Edit handle
@dp.message(F.from_user.id == ADMIN_ID)
async def handle_edit(msg: Message):
    edit_type = dp.data.get("edit_type")
    if not edit_type:
        return
    if "|" not in msg.text:
        await msg.answer("❌ Format noto‘g‘ri. Kod|Yangi nom")
        return
    code, new_title = [p.strip() for p in msg.text.split("|", 1)]
    table = "movies" if edit_type == "movie" else "serials"
    cur.execute(f"UPDATE {table} SET title=? WHERE code=?", (new_title, code))
    db.commit()
    await msg.answer(f"✅ {edit_type.capitalize()} kodi {code} tahrirlandi!")
    dp.data["edit_type"] = None

# =================== LIST ===================
@dp.callback_query(F.data == "admin_list_movies")
async def list_movies(call: CallbackQuery):
    cur.execute("SELECT code,title FROM movies")
    movies = cur.fetchall()
    if not movies:
        await call.message.answer("🎬 Kino yo‘q")
        return
    text = "🎬 Kino ro‘yxati:\n" + "\n".join([f"{m[0]} - {m[1]}" for m in movies])
    await call.message.answer(text)

@dp.callback_query(F.data == "admin_list_serials")
async def list_serials(call: CallbackQuery):
    cur.execute("SELECT code,title FROM serials")
    serials = cur.fetchall()
    if not serials:
        await call.message.answer("🎞 Serial yo‘q")
        return
    text = "🎞 Serial ro‘yxati:\n" + "\n".join([f"{s[0]} - {s[1]}" for s in serials])
    await call.message.answer(text)

# =================== USERS & STATS ===================
@dp.callback_query(F.data == "admin_users")
async def admin_users(call: CallbackQuery):
    cur.execute("SELECT user_id, username FROM users")
    users = cur.fetchall()
    if not users:
        await call.message.answer("👥 Foydalanuvchi yo‘q")
        return
    text = "👥 Foydalanuvchilar ro‘yxati:\n\n" + "\n".join([f"{u[0]} - @{u[1] if u[1] else 'No username'}" for u in users])
    await call.message.answer(text)

@dp.callback_query(F.data == "admin_stats")
async def admin_stats(call: CallbackQuery):
    cur.execute("SELECT COUNT(*) FROM users")
    total_users = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM movies")
    total_movies = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM serials")
    total_serials = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM saved")
    total_saved = cur.fetchone()[0]
    text = f"""📊 Bot statistika:
👥 Foydalanuvchilar: {total_users}
🎬 Kinolar: {total_movies}
🎞 Seriallar: {total_serials}
💾 Saqlangan: {total_saved}"""
    await call.message.answer(text)

# =================== BROADCAST ===================
@dp.callback_query(F.data == "admin_broadcast_inline")
async def admin_broadcast_inline(call: CallbackQuery):
    await call.message.answer("📣 Inline tugma bilan xabar yuboring.\nFormat: Xabar matni | Tugma matni | URL")
    dp.data["broadcast_type"] = "inline"
    await call.answer()

@dp.callback_query(F.data == "admin_broadcast_text")
async def admin_broadcast_text(call: CallbackQuery):
    await call.message.answer("📢 Tugmasiz xabar yuboring.")
    dp.data["broadcast_type"] = "text"
    await call.answer()

@dp.message(F.from_user.id == ADMIN_ID)
async def handle_broadcast(msg: Message):
    broadcast_type = dp.data.get("broadcast_type")
    if not broadcast_type:
        return

    cur.execute("SELECT user_id FROM users")
    users = cur.fetchall()
    if not users:
        await msg.answer("❌ Foydalanuvchi yo‘q")
        dp.data["broadcast_type"] = None
        return

    if broadcast_type == "inline":
        if not msg.text or "|" not in msg.text:
            await msg.answer("❌ Format noto‘g‘ri. Format: Xabar matni | Tugma matni | URL")
            return
        text, btn_text, url = [p.strip() for p in msg.text.split("|", 2)]
        kb = InlineKeyboardBuilder()
        kb.button(text=btn_text, url=url)
        kb.adjust(1)
        sent_count = 0
        for u in users:
            try:
                await bot.send_message(u[0], text, reply_markup=kb.as_markup())
                sent_count += 1
            except:
                continue
        await msg.answer(f"✅ Xabar {sent_count} foydalanuvchiga yuborildi!")
    else:
        sent_count = 0
        for u in users:
            try:
                await bot.send_message(u[0], msg.text)
                sent_count += 1
            except:
                continue
        await msg.answer(f"✅ Xabar {sent_count} foydalanuvchiga yuborildi!")

    dp.data["broadcast_type"] = None

# =================== RUN ===================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
