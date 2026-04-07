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
CREATE TABLE IF NOT EXISTS serials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE,
    title TEXT,
    file_id TEXT
)
""")
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
    cur.execute("SELECT id, title, file_id FROM movies WHERE title LIKE ?", (f"%{text}%",))
    for m in cur.fetchall():
        kb = InlineKeyboardBuilder()
        kb.button(text="💾 Saqlash", callback_data=f"save_movie_{m[0]}")
        results.append(InlineQueryResultCachedVideo(id=f"m{m[0]}", video_file_id=m[2], title=m[1], reply_markup=kb.as_markup()))
    cur.execute("SELECT id, title, file_id FROM serials WHERE title LIKE ?", (f"%{text}%",))
    for s in cur.fetchall():
        kb = InlineKeyboardBuilder()
        kb.button(text="💾 Saqlash", callback_data=f"save_serial_{s[0]}")
        results.append(InlineQueryResultCachedVideo(id=f"s{s[0]}", video_file_id=s[2], title=s[1], reply_markup=kb.as_markup()))
    await query.answer(results, cache_time=1)

# =================== KOD ORQALI KINO ===================
@dp.message(F.text.regexp(r"^\d{1,10}$"))
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

# =================== ADMIN KINO/SERIAL CRUD ===================
async def send_admin_list(msg: Message, table, name):
    cur.execute(f"SELECT id, code, title FROM {table}")
    data = cur.fetchall()
    if not data:
        await msg.answer(f"{name} yo‘q")
        return
    text = f"{name} ro‘yxati:\n\n" + "\n".join([f"ID: {d[0]} | Kod: {d[1]} | {d[2]}" for d in data])
    await msg.answer(text)

# Qo‘shish
@dp.callback_query(F.data == "admin_add_movie")
async def admin_add_movie(call: CallbackQuery):
    dp.data["admin_action"] = "add_movie"
    await call.message.answer("🎬 Kino qo‘shish: Kod | Nomi | file_id formatda yuboring")
    await call.answer()
@dp.callback_query(F.data == "admin_add_serial")
async def admin_add_serial(call: CallbackQuery):
    dp.data["admin_action"] = "add_serial"
    await call.message.answer("🎞 Serial qo‘shish: Kod | Nomi | file_id formatda yuboring")
    await call.answer()

# O‘chirish
@dp.callback_query(F.data == "admin_delete_movie")
async def admin_delete_movie(call: CallbackQuery):
    dp.data["admin_action"] = "delete_movie"
    await send_admin_list(call.message, "movies", "Kinolar")
    await call.message.answer("O‘chirmoqchi bo‘lgan kinoning ID raqamini yuboring")
    await call.answer()
@dp.callback_query(F.data == "admin_delete_serial")
async def admin_delete_serial(call: CallbackQuery):
    dp.data["admin_action"] = "delete_serial"
    await send_admin_list(call.message, "serials", "Seriallar")
    await call.message.answer("O‘chirmoqchi bo‘lgan serialning ID raqamini yuboring")
    await call.answer()

# Tahrirlash
@dp.callback_query(F.data == "admin_edit_movie")
async def admin_edit_movie(call: CallbackQuery):
    dp.data["admin_action"] = "edit_movie"
    await send_admin_list(call.message, "movies", "Kinolar")
    await call.message.answer("Tahrirlash uchun ID | Kod | Nomi | file_id formatda yuboring")
    await call.answer()
@dp.callback_query(F.data == "admin_edit_serial")
async def admin_edit_serial(call: CallbackQuery):
    dp.data["admin_action"] = "edit_serial"
    await send_admin_list(call.message, "serials", "Seriallar")
    await call.message.answer("Tahrirlash uchun ID | Kod | Nomi | file_id formatda yuboring")
    await call.answer()

# Admin input handler
@dp.message(F.from_user.id == ADMIN_ID)
async def admin_input_handler(msg: Message):
    action = dp.data.get("admin_action")
    if not action:
        return
    text = msg.text.strip()
    if action == "add_movie":
        try:
            code, title, file_id = [p.strip() for p in text.split("|", 2)]
            cur.execute("INSERT INTO movies (code,title,file_id) VALUES (?,?,?)",(code,title,file_id))
            db.commit()
            await msg.answer("✅ Kino qo‘shildi")
        except:
            await msg.answer("❌ Format xato yoki kod mavjud")
    elif action == "add_serial":
        try:
            code, title, file_id = [p.strip() for p in text.split("|", 2)]
            cur.execute("INSERT INTO serials (code,title,file_id) VALUES (?,?,?)",(code,title,file_id))
            db.commit()
            await msg.answer("✅ Serial qo‘shildi")
        except:
            await msg.answer("❌ Format xato yoki kod mavjud")
    elif action == "delete_movie":
        try:
            id_ = int(text)
            cur.execute("DELETE FROM movies WHERE id=?",(id_,))
            db.commit()
            await msg.answer("✅ Kino o‘chirildi")
        except:
            await msg.answer("❌ ID xato")
    elif action == "delete_serial":
        try:
            id_ = int(text)
            cur.execute("DELETE FROM serials WHERE id=?",(id_,))
            db.commit()
            await msg.answer("✅ Serial o‘chirildi")
        except:
            await msg.answer("❌ ID xato")
    elif action == "edit_movie":
        try:
            id_, code, title, file_id = [p.strip() for p in text.split("|",3)]
            cur.execute("UPDATE movies SET code=?, title=?, file_id=? WHERE id=?",(code,title,file_id,id_))
            db.commit()
            await msg.answer("✅ Kino tahrirlandi")
        except:
            await msg.answer("❌ Format xato")
    elif action == "edit_serial":
        try:
            id_, code, title, file_id = [p.strip() for p in text.split("|",3)]
            cur.execute("UPDATE serials SET code=?, title=?, file_id=? WHERE id=?",(code,title,file_id,id_))
            db.commit()
            await msg.answer("✅ Serial tahrirlandi")
        except:
            await msg.answer("❌ Format xato")
    dp.data["admin_action"] = None

# =================== FOYDALANUVCHI RO'YXATI ===================
@dp.callback_query(F.data == "admin_users")
async def admin_users(call: CallbackQuery):
    cur.execute("SELECT user_id, username FROM users")
    users = cur.fetchall()
    if not users:
        await call.message.answer("👥 Foydalanuvchi yo‘q")
        return
    text = "👥 Foydalanuvchilar ro‘yxati:\n\n" + "\n".join([f"{u[0]} - @{u[1] if u[1] else 'No username'}" for u in users])
    await call.message.answer(text)

# =================== ADMIN STATISTIKA ===================
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

# =================== ADMIN BROADCAST ===================
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
