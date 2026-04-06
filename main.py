 import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineQuery, InlineQueryResultCachedVideo
from aiogram.utils.keyboard import InlineKeyboardBuilder

# =================== SOZLAMALAR ===================
BOT_TOKEN = "7748673962:AAE0KUclQJs6xcwlsFnKvcmhvfl5TpwsxYI"  # <=== Shu yerga tokeningiz
ADMIN_ID = 6884014716
CHANNEL_USERNAME = "@kinolashamz"
DB_PATH = "/tmp/kino.db"
# ====================================================

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

# =================== DATABASE ===================
db = sqlite3.connect(DB_PATH, check_same_thread=False)
cur = db.cursor()
db.execute("PRAGMA journal_mode=WAL;")

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    is_premium INTEGER DEFAULT 0
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS movies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE,
    title TEXT,
    file_id TEXT,
    is_premium INTEGER DEFAULT 0
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS saved (
    user_id INTEGER,
    movie_id INTEGER
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
    user_id = msg.from_user.id
    param = msg.text.split()[1] if len(msg.text.split()) > 1 else None

    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Kanalga obuna bo‘lish", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")
    kb.button(text="🔍 Obunani tekshirish", callback_data="check_sub")
    kb.adjust(2)

    if not await check_sub(user_id):
        text = (
            f"👋 Assalomu alaykum [{user_name}](tg://user?id={user_id})!\n\n"
            "🎬 Botdagi barcha eng zo‘r filmlarni tomosha qilish uchun faqat **1ta rasmiy kanalimizga obuna bo‘ling**.\n\n"
            "💡 Kanalga obuna bo‘lgach, siz barcha filmlarga kirish huquqiga ega bo‘lasiz!"
        )
        await msg.answer_photo(
            photo="URL_OF_ADMIN_IMAGE_HERE",  # Shu yerga admin rasm qo‘shadi
            caption=text,
            reply_markup=kb.as_markup(),
            parse_mode="Markdown"
        )
        return

    cur.execute("INSERT OR IGNORE INTO users(user_id,username) VALUES (?,?)",
                (user_id, msg.from_user.username))
    db.commit()

    kb_main = InlineKeyboardBuilder()
    kb_main.button(text="🔍 Inline qidiruv", switch_inline_query_current_chat="")
    kb_main.button(text="💾 Saqlangan filmlar", callback_data="my_movies")
    kb_main.adjust(1)

    await msg.answer(f"🎬 Xush kelibsiz {user_name}", reply_markup=kb_main.as_markup())

# =================== CHECK SUB ===================
@dp.callback_query(F.data == "check_sub")
async def check_subscription(call: CallbackQuery):
    if await check_sub(call.from_user.id):
        cur.execute("INSERT OR IGNORE INTO users(user_id,username) VALUES (?,?)",
                    (call.from_user.id, call.from_user.username))
        db.commit()
        await call.message.edit_text("✅ Obuna tasdiqlandi. Botdan foydalanishingiz mumkin.")
    else:
        await call.answer("❌ Avval kanalga obuna bo‘ling", show_alert=True)

# =================== INLINE QIDIRUV ===================
@dp.inline_query()
async def inline_search(query: InlineQuery):
    cur.execute("SELECT id,title,file_id,is_premium FROM movies WHERE title LIKE ?",
                (f"%{query.query}%",))
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

# =================== SAQLASH ===================
@dp.callback_query(F.data.startswith("save_"))
async def save_movie(call: CallbackQuery):
    movie_id = int(call.data.split("_")[1])
    cur.execute("INSERT OR IGNORE INTO saved(user_id,movie_id) VALUES (?,?)",
                (call.from_user.id, movie_id))
    db.commit()
    await call.answer("💾 Saqlandi")

# =================== SAQLANGAN FILMLAR ===================
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

# =================== ADMIN PANEL ===================
@dp.message(F.from_user.id == ADMIN_ID, F.text.startswith("/admin"))
async def admin_panel(msg: Message):
    kb = InlineKeyboardBuilder()
    kb.button(text="📊 Foydalanuvchi statistikasi", callback_data="stats")
    kb.button(text="📢 Xabar yuborish", callback_data="broadcast")
    kb.button(text="💎 Premium foydalanuvchi qo‘shish", callback_data="premium_user")
    kb.adjust(1)
    await msg.answer("⚙️ Admin panel:", reply_markup=kb.as_markup())

# =================== STATISTIKA ===================
@dp.callback_query(F.data == "stats")
async def admin_stats(call: CallbackQuery):
    cur.execute("SELECT COUNT(*) FROM users")
    total_users = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM movies")
    total_movies = cur.fetchone()[0]
    await call.message.answer(f"👥 Foydalanuvchilar: {total_users}\n🎬 Filmlar: {total_movies}")

# =================== BROADCAST ===================
@dp.callback_query(F.data == "broadcast")
async def admin_broadcast(call: CallbackQuery):
    await call.message.answer("📢 Xabarni yozing, men barcha foydalanuvchilarga yuboraman.")
    # Keyingi yozilgan xabarni olish va barcha foydalanuvchilarga yuborish kodini qo‘shish mumkin

# =================== PREMIUM FOYDALANUVCHI ===================
@dp.callback_query(F.data == "premium_user")
async def admin_premium(call: CallbackQuery):
    await call.message.answer("💎 Premium foydalanuvchi ID sini kiriting:")

# =================== RUN ===================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
