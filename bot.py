import asyncio, os, sqlite3
from dotenv import load_dotenv
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo

load_dotenv()
TOKEN = os.environ["BOT_TOKEN"]
WEBAPP_URL = os.environ["WEBAPP_URL"]
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
REF_COINS = 2

db = sqlite3.connect("data.db")
db.execute("""CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY, name TEXT, username TEXT,
    coins INTEGER DEFAULT 0, invited INTEGER DEFAULT 0, ref_by INTEGER)""")
db.commit()

bot = Bot(TOKEN)
dp = Dispatcher()


def menu():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Darslarni ochish", web_app=WebAppInfo(url=WEBAPP_URL))
    ]])


@dp.message(CommandStart())
async def start(m: Message, command: CommandObject):
    u = m.from_user
    exists = db.execute("SELECT 1 FROM users WHERE id=?", (u.id,)).fetchone()
    if not exists:
        ref = None
        arg = command.args or ""
        if arg.startswith("ref_") and arg[4:].isdigit():
            ref = int(arg[4:])
        if ref == u.id or not db.execute("SELECT 1 FROM users WHERE id=?", (ref,)).fetchone():
            ref = None
        db.execute("INSERT INTO users(id,name,username,ref_by) VALUES(?,?,?,?)",
                   (u.id, u.full_name, u.username, ref))
        if ref:
            db.execute("UPDATE users SET coins=coins+?, invited=invited+1 WHERE id=?", (REF_COINS, ref))
            try:
                await bot.send_message(ref, f"Doʻstingiz {u.full_name} qoʻshildi. Sizga +{REF_COINS} coin berildi.")
            except Exception:
                pass
        db.commit()
    await m.answer(
        f"Salom, {u.first_name}! Frontend Develop botiga xush kelibsiz.\n"
        "Pastdagi tugma orqali darslarni oching.", reply_markup=menu())


@dp.message(Command("coins"))
async def coins(m: Message):
    r = db.execute("SELECT coins, invited FROM users WHERE id=?", (m.from_user.id,)).fetchone()
    if not r:
        return await m.answer("Avval /start bosing.")
    await m.answer(f"Coinlaringiz: {r[0]}\nTaklif qilganlar: {r[1]}\n\n"
                   f"Havolangiz:\nhttps://t.me/{(await bot.me()).username}?start=ref_{m.from_user.id}")


@dp.message(Command("stats"))
async def stats(m: Message):
    if m.from_user.id != ADMIN_ID:
        return
    n = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    top = db.execute("SELECT name, invited, coins FROM users ORDER BY invited DESC LIMIT 5").fetchall()
    lines = "\n".join(f"{i+1}. {t[0]} - {t[1]} doʻst, {t[2]} coin" for i, t in enumerate(top))
    await m.answer(f"Foydalanuvchilar: {n}\n\nEng koʻp taklif qilganlar:\n{lines}")


async def health(request):
    return web.Response(text="ok")


async def main():
    port = os.environ.get("PORT")
    if port:  # Render web service uchun kichik veb-manzil
        app = web.Application()
        app.router.add_get("/", health)
        runner = web.AppRunner(app)
        await runner.setup()
        await web.TCPSite(runner, "0.0.0.0", int(port)).start()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
