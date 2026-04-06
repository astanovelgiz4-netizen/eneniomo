import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, F, types
from aiogram.types import Message, CallbackQuery, InlineQuery, InlineQueryResultCachedVideo
from aiogram.utils.keyboard import InlineKeyboardBuilder

BOT_TOKEN = "7748673962:AAE0KUclQJs6xcwlsFnKvcmhvfl5TpwsxYI"
ADMIN_ID = 6884014716
CHANNEL_USERNAME = "@kinolashamz"
DB_PATH = "/tmp/kino.db"

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

db = sqlite3.connect(DB_PATH, check_same_thread=False)
cur = db.cursor()
db.execute("PRAGMA journal_mode=WAL;")

# Tables
cur.execute("""CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    is_premium INTEGER DEFAULT 0
)""")

cur.execute("""CREATE TABLE IF NOT EXISTS movies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE,
    title TEXT,
    file_id TEXT,
    is_premium INTEGER DEFAULT 0
)""")

cur.execute("""CREATE TABLE IF NOT EXISTS saved (
    user_id INTEGER,
    movie_id INTEGER
)""")
db.commit()

# Temp storage for admin actions
admin_state = {}

# ---------- HELPERS ----------
async def check_sub(user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# ---------- START ----------
@dp.message(F.text.startswith("/start"))
async def start(msg: Message):
    user_name = msg.from_user.full_name
    user_id = msg.from_user.id

    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Kanalga obuna bo‘lish", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")
    kb.button(text="🔍 Obunani tekshirish", callback_data="check_sub")
    kb.adjust(2)

    if not await check_sub(user_id):
        text = f"👋 Assalomu alaykum [{user_name}](tg://user?id={user_id})!\n\n" \
               "🎬 Botdagi barcha eng zo‘r filmlarni tomosha qilish uchun faqat **1ta rasmiy kanalimizga obuna bo‘ling**.\n\n" \
               "💡 Kanalga obuna bo‘lgach, siz barcha filmlarga kirish huquqiga ega bo‘lasiz!"
        await msg.answer_photo(photo="URL_OF_ADMIN_IMAGE_HERE", caption=text, reply_markup=kb.as_markup(), parse_mode="Markdown")
        return

    cur.execute("INSERT OR IGNORE INTO users(user_id,username) VALUES (?,?)", (user_id, msg.from_user.username))
    db.commit()

    kb_main = InlineKeyboardBuilder()
    kb_main.button(text="🔍 Inline qidiruv", switch_inline_query_current_chat="")
    kb_main.button(text="💾 Saqlangan filmlar", callback_data="my_movies")
    kb_main.adjust(1)
    await msg.answer(f"🎬 Xush kelibsiz {user_name}", reply_markup=kb_main.as_markup())

# ---------- CHECK SUB ----------
@dp.callback_query(F.data == "check_sub")
async def check_subscription(call: CallbackQuery):
    if await check_sub(call.from_user.id):
        cur.execute("INSERT OR IGNORE INTO users(user_id,username) VALUES (?,?)",
                    (call.from_user.id, call.from_user.username))
        db.commit()
        await call.message.edit_text("✅ Obuna tasdiqlandi. Botdan foydalanishingiz mumkin.")
    else:
        await call.answer("❌ Avval kanalga obuna bo‘ling", show_alert=True)

# ---------- INLINE SEARCH ----------
@dp.inline_query()
async def inline_search(query: InlineQuery):
    cur.execute("SELECT id,title,file_id,is_premium FROM movies WHERE title LIKE ?", (f"%{query.query}%",))
    movies = cur.fetchall()
    results = []

    for m in movies:
        if m[3] == 1:
            cur.execute("SELECT is_premium FROM users WHERE user_id=?", (query.from_user.id,))
            user_premium = cur.fetchone()
            if not user_premium or user_premium[0] == 0:
                continue
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

# ---------- SAVE MOVIE ----------
@dp.callback_query(F.data.startswith("save_"))
async def save_movie(call: CallbackQuery):
    movie_id = int(call.data.split("_")[1])
    cur.execute("INSERT OR IGNORE INTO saved(user_id,movie_id) VALUES (?,?)", (call.from_user.id, movie_id))
    db.commit()
    await call.answer("💾 Saqlandi")

# ---------- MY MOVIES ----------
@dp.callback_query(F.data == "my_movies")
async def my_movies(call: CallbackQuery):
    cur.execute("""
        SELECT movies.title, movies.file_id, movies.is_premium
        FROM movies
        JOIN saved ON movies.id = saved.movie_id
        WHERE saved.user_id=?
    """, (call.from_user.id,))
    movies = cur.fetchall()

    if not movies:
        await call.message.answer("💤 Sizda saqlangan kino yo‘q")
        return

    for title, file_id, is_premium in movies:
        kb = InlineKeyboardBuilder()
        kb.button(text="💾 Saqlash", callback_data=f"save_{file_id}")
        kb.adjust(1)
        premium_tag = " 🔒 Premium" if is_premium else ""
        await bot.send_video(call.from_user.id, file_id, caption=f"🎬 {title}{premium_tag}", reply_markup=kb.as_markup())

# ---------- ADMIN PANEL ----------
@dp.message(F.from_user.id == ADMIN_ID, F.text.startswith("/admin"))
async def admin_panel(msg: Message):
    kb = InlineKeyboardBuilder()
    kb.button(text="📊 Statistikasi", callback_data="stats")
    kb.button(text="📢 Xabar yuborish", callback_data="broadcast")
    kb.button(text="💎 Premium qo‘shish", callback_data="premium_user")
    kb.button(text="🎬 Film qo‘shish", callback_data="add_movie")
    kb.button(text="🗑 Film o‘chirish", callback_data="delete_movie")
    kb.adjust(1)
    await msg.answer("⚙️ Admin panel:", reply_markup=kb.as_markup())

# ---------- ADMIN HANDLERS ----------
@dp.callback_query(F.data == "stats")
async def admin_stats(call: CallbackQuery):
    cur.execute("SELECT COUNT(*) FROM users")
    total_users = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM movies")
    total_movies = cur.fetchone()[0]
    await call.message.answer(f"👥 Foydalanuvchilar: {total_users}\n🎬 Filmlar: {total_movies}")

@dp.callback_query(F.data == "broadcast")
async def admin_broadcast(call: CallbackQuery):
    admin_state[call.from_user.id] = "broadcast"
    await call.message.answer("📢 Xabarni yozing:")

@dp.message(F.from_user.id == ADMIN_ID)
async def handle_admin_messages(msg: Message):
    uid = msg.from_user.id
    if uid in admin_state:
        state = admin_state[uid]
        if state == "broadcast":
            cur.execute("SELECT user_id FROM users")
            users = cur.fetchall()
            for u in users:
                try:
                    await bot.send_message(u[0], msg.text)
                except: 
                    continue
            await msg.answer("✅ Xabar barcha foydalanuvchilarga yuborildi!")
            admin_state.pop(uid)
        elif state == "premium_user":
            try:
                user_id = int(msg.text)
                cur.execute("UPDATE users SET is_premium=1 WHERE user_id=?", (user_id,))
                db.commit()
                await msg.answer(f"💎 {user_id} premium foydalanuvchi qilindi!")
            except:
                await msg.answer("❌ ID noto‘g‘ri!")
            admin_state.pop(uid)
        elif state == "add_movie_caption":
            # Video file already received
            try:
                caption = msg.caption
                code, title, premium_text = caption.split("|")
                is_premium = 1 if premium_text.strip().lower() == "ha" else 0
                cur.execute("INSERT INTO movies(code,title,file_id,is_premium) VALUES (?,?,?,?)",
                            (code.strip(), title.strip(), admin_state[uid]["file_id"], is_premium))
                db.commit()
                await msg.answer(f"🎬 Film '{title}' qo‘shildi! Premium: {'Ha' if is_premium else 'Yo\'q'}")
            except Exception as e:
                await msg.answer(f"❌ Xato! Format: `001|Kino nomi|ha/yo'q`\n{e}")
            admin_state.pop(uid)

@dp.callback_query(F.data == "premium_user")
async def admin_premium(call: CallbackQuery):
    admin_state[call.from_user.id] = "premium_user"
    await call.message.answer("💎 Premium foydalanuvchi ID sini kiriting:")

@dp.callback_query(F.data == "add_movie")
async def admin_add_movie(call: CallbackQuery):
    admin_state[call.from_user.id] = {}
    await call.message.answer("🎬 Video yuboring (premium/yo'qni captionda yozing: `001|Kino nomi|ha/yo'q`)")

@dp.message(F.content_type == "video", F.from_user.id == ADMIN_ID)
async def receive_movie_video(msg: Message):
    uid = msg.from_user.id
    if uid in admin_state:
        admin_state[uid]["file_id"] = msg.video.file_id
        admin_state[uid] = "add_movie_caption"
        await msg.answer("📌 Endi caption yozing: `001|Kino nomi|ha/yo'q`")

@dp.callback_query(F.data == "delete_movie")
async def admin_delete_movie(call: CallbackQuery):
    admin_state[call.from_user.id] = "delete_movie"
    await call.message.answer("🎬 O‘chirmoqchi bo‘lgan film kodini yozing:")

@dp.message(F.from_user.id == ADMIN_ID)
async def handle_delete(msg: Message):
    uid = msg.from_user.id
    if uid in admin_state and admin_state[uid] == "delete_movie":
        try:
            code = msg.text.strip()
            cur.execute("DELETE FROM movies WHERE code=?", (code,))
            db.commit()
            await msg.answer(f"🗑 Film '{code}' o‘chirildi!")
        except:
            await msg.answer("❌ Kod noto‘g‘ri yoki film topilmadi.")
        admin_state.pop(uid)

# ---------- RUN ----------
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
