import os
import telebot
from telebot import types
import sqlite3
import math
from flask import Flask
from threading import Thread

# --- 1. RENDER SETUP ---
app = Flask(__name__)
@app.route('/')
def home(): return "ABRSH BOT IS LIVE"
def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

# --- 2. BOT CONFIG ---
TOKEN = "8673546825:AAG3tqrnD_STYgf5gtyjVdbw8awXUQD1m10"
ADMIN_ID = 7908276494 
bot = telebot.TeleBot(TOKEN, parse_mode="Markdown")

# --- 3. DATABASE ---
def init_db():
    conn = sqlite3.connect('abrsh_final.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 5.0)')
    c.execute('CREATE TABLE IF NOT EXISTS movies (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, file_id TEXT, price REAL, category TEXT)')
    conn.commit()
    return conn

conn = init_db()
user_states = {}

def main_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("※ ፊልም ልይ!", "※ ያለኝ ሂሳብ!")
    markup.row("※ ገቢ ላድርግ!", "※ ጎደኛዬን ልጋብዝ!")
    markup.row("※ አጠቃቀም!", "※ DM ABRSH!")
    return markup

# --- 4. START HANDLER ---
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    c = conn.cursor()
    if not c.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,)).fetchone():
        c.execute("INSERT INTO users (user_id, balance) VALUES (?, ?)", (user_id, 5.0))
        conn.commit()

    welcome_text = (
        "**※ ሰላም ይህ የ ABRSH Movies Bot ነው እንኳን በደህና መጡ!**\n\n"
        "**※ በትረጉም ፊልሞቻችን ይዝናኑ!**\n\n"
        "**※ ፊልም ልይ'ን ይጫኑ ና ደስታዎን ያስጀምሩ!**"
    )
    photo = "https://i.ibb.co/8Dt8G2Ps/5930522196038061317-120.jpg"
    
    bot.send_photo(message.chat.id, photo, caption=welcome_text, reply_markup=main_markup())
    
    if user_id == ADMIN_ID:
        admin_kb = types.InlineKeyboardMarkup(row_width=1)
        admin_kb.add(
            types.InlineKeyboardButton("📊 Bot Statics", callback_data="admin_stats"),
            types.InlineKeyboardButton("📂 Upload Movies", callback_data="admin_upload"),
            types.InlineKeyboardButton("⚙️ Manage Movies", callback_data="admin_manage")
        )
        bot.send_message(message.chat.id, "🛠 **Admin Control Panel:**", reply_markup=admin_kb)

# --- 5. ADMIN: UPLOAD & MANAGE ---
@bot.callback_query_handler(func=lambda c: c.data == "admin_upload")
def start_upload(call):
    msg = bot.send_message(ADMIN_ID, "📂 **ቪዲዮውን ይላኩ (Caption ላይ ስሙን ይጻፉ)...**")
    bot.register_next_step_handler(msg, process_video_upload)

def process_video_upload(message):
    if not message.video and not message.document:
        bot.send_message(ADMIN_ID, "❌ እባክዎ ቪዲዮ ወይም ፋይል ይላኩ!")
        return
    file_id = message.video.file_id if message.video else message.document.file_id
    movie_name = message.caption if message.caption else "ያልተሰየመ ፊልም"
    user_states[ADMIN_ID] = {'f_id': file_id, 'name': movie_name}
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    colors = [("⚫️", 0.5), ("🟢", 0.5), ("🟡", 0.3), ("🔴", 1.0), ("🔵", 0.5), ("🟣", 0.5), ("🟠", 0.3), ("⚪️", 5.0)]
    for icon, price in colors:
        markup.insert(types.InlineKeyboardButton(f"{icon} {price} ብር", callback_data=f"save_{icon}_{price}"))
    bot.send_message(ADMIN_ID, f"🎬 **ፊልም፦ {movie_name}**\nአይነቱን ይምረጡ፦", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("save_"))
def save_movie(call):
    _, icon, price = call.data.split("_")
    data = user_states.get(ADMIN_ID)
    if data:
        conn.execute("INSERT INTO movies (name, file_id, price, category) VALUES (?, ?, ?, ?)", (data['name'], data['f_id'], float(price), icon))
        conn.commit()
        bot.edit_message_text(f"✅ **{data['name']}** በትክክል ተጭኗል!", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda c: c.data == "admin_manage")
def manage_movies(call):
    movies = conn.execute("SELECT id, name FROM movies ORDER BY id DESC LIMIT 20").fetchall()
    markup = types.InlineKeyboardMarkup()
    for m_id, m_name in movies:
        markup.add(types.InlineKeyboardButton(f"❌ {m_name}", callback_data=f"del_{m_id}"))
    bot.send_message(ADMIN_ID, "⚙️ **ለማጥፋት የሚፈልጉትን ፊልም ይጫኑ፦**", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("del_"))
def delete_movie(call):
    m_id = call.data.split("_")[1]
    conn.execute("DELETE FROM movies WHERE id = ?", (m_id,))
    conn.commit()
    bot.edit_message_text("✅ ፊልሙ ተሰርዟል!", call.message.chat.id, call.message.message_id)

# --- 6. USER: SEARCH & USAGE ---
@bot.message_handler(func=lambda m: m.text == "※ ፊልም ልይ!")
def search_init(message):
    msg = bot.send_message(message.chat.id, "⨳ **የሚፈልጉትን ፊልም ስም ይፃፉ!**")
    bot.register_next_step_handler(msg, process_search)

def process_search(message):
    query = message.text
    res = conn.execute("SELECT id, name, category, price FROM movies WHERE name LIKE ?", (f'%{query}%',)).fetchall()
    if not res:
        bot.send_message(message.chat.id, "⨳ **በዚ ስም የተሰየመ ፊልም ማግኘት አልቻልኩም!**\n⨳ **ፊደል ተሳስተው እንዳይሆን ያረጋግጡ!**")
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for r in res[:10]: markup.add(types.InlineKeyboardButton(f"{r[2]} {r[1]} - {r[3]} ብር", callback_data=f"buy_{r[0]}"))
    bot.send_message(message.chat.id, f"🔍 **ውጤቶች ለ '{query}'**", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "※ አጠቃቀም!")
def usage_instruction(message):
    usage_text = (
        "**🧶 የICON ከለሮች ትርጉም።**\n"
        "**\">\">\">\">\">\">\">\">**\n"
        "**⚫️ -> ትርጉም ተከታታይ እና ሲንግል!**\n"
        "**🟢 -> ሲንግል!**\n"
        "**🟡 -> ተከታታይ ትርጉም!**\n"
        "**🔴 -> ሮማንስ ያለ ትርጉም!**\n"
        "**🔵 -> አማርኛ!**\n"
        "**🟣 -> ተከታታይ አማርኛ!**\n"
        "**🟠 -> ቃና ፊልሞች!**\n"
        "**⚪️ -> መፅሀፍት!**\n"
        "**\">\">\">\">\">\">\">\">**\n"
        "**💵 የፊልሞች ዋጋ**\n"
        "**💰ሲንግል -> 0.5 ብር።**\n"
        "**💰ተከታታይ -> 0.3 ብር።**\n"
        "**💰አማርኛ -> 0.5 ብር።**\n"
        "**💰ኢሮቲክ -> 1 ብር።**\n"
        "**💰ተከታታይ አማርኛ -> 0.5 ብር።**\n"
        "**💰ቃና -> 0.3 ብር።**\n"
        "**💰መፅሀፍ -> 5 ብር።**\n"
        "**\">\">\">\">\">\">\">\">**\n"
        "**✅ @ABRSHFILMBET**"
    )
    bot.send_message(message.chat.id, usage_text)

# --- 7. OTHER BTNS ---
@bot.message_handler(func=lambda m: True)
def other_btns(m):
    if m.text == "※ ያለኝ ሂሳብ!":
        res = conn.execute("SELECT balance FROM users WHERE user_id=?", (m.from_user.id,)).fetchone()
        bot.send_message(m.chat.id, f"**⨳ ቀሪ ሂሳብ ~> {res[0] if res else 0.0} ብር**")
    elif m.text == "※ DM ABRSH!":
        bot.send_message(m.chat.id, "**የዚህ ቦት Owner👉 @ABRSHFILMBET**")
    elif m.text == "※ ገቢ ላድርግ!":
        kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("Telebirr", callback_data="t_b"))
        bot.send_message(m.chat.id, "⨳ **ገቢ የሚያደርጉበት መንገድ ቴሌብር ነው!**", reply_markup=kb)
    elif m.text == "※ ጎደኛዬን ልጋብዝ!":
        link = f"https://t.me/ABRSHMovies_Bot?start=ref{m.from_user.id}"
        bot.send_message(m.chat.id, f"**ጓደኞችዎን ይጋብዙ!**\n\n1 ሰው ሲጋብዙ > 0.7 ብር ያገኛሉ!\n\n{link}")

@bot.callback_query_handler(func=lambda c: True)
def global_calls(c):
    if c.data == "admin_stats":
        u = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        m = conn.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
        bot.answer_callback_query(c.id, f"Users: {u} | Movies: {m}", show_alert=True)
    elif c.data == "t_b":
        bot.send_message(c.message.chat.id, "⨳ **በዚህ +251961343796 ስልክ ቁጥር በቴሌብር ከ5 ብር ጀምሮ በማስገባት Screen Shoot ላኩ።**")

if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.polling(none_stop=True)
