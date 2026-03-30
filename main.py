import os
import telebot
from telebot import types
import sqlite3
import math
from flask import Flask
from threading import Thread

# --- 1. RENDER SERVER SETUP ---
app = Flask(__name__)
@app.route('/')
def home(): return "ABRSH BOT IS LIVE"
def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

# --- 2. BOT CONFIGURATION ---
TOKEN = "8673546825:AAG3tqrnD_STYgf5gtyjVdbw8awXUQD1m10"
ADMIN_ID = 7908276494 
bot = telebot.TeleBot(TOKEN, parse_mode="Markdown")

# --- 3. DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('abrsh_final.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 5.0)')
    c.execute('CREATE TABLE IF NOT EXISTS movies (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, file_id TEXT, price REAL, category TEXT)')
    conn.commit()
    return conn

db_conn = init_db()
user_states = {}

# --- 4. KEYBOARDS ---
def main_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("※ ፊልም ልይ!", "※ ያለኝ ሂሳብ!")
    markup.row("※ ገቢ ላድርግ!", "※ ጎደኛዬን ልጋብዝ!")
    markup.row("※ አጠቃቀም!", "※ DM ABRSH!")
    return markup

# --- 5. START & ADMIN PANEL ---
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    c = db_conn.cursor()
    
    # አዲስ ተጠቃሚ መመዝገብ
    if not c.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,)).fetchone():
        c.execute("INSERT INTO users (user_id, balance) VALUES (?, ?)", (user_id, 5.0))
        db_conn.commit()

    welcome_text = (
        "**※ ሰላም ይህ የ ABRSH Movies Bot ነው እንኳን በደህና መጡ!**\n\n"
        "**※ በትረጉም ፊልሞቻችን ይዝናኑ!**\n\n"
        "**※ ፊልም ልይ'ን ይጫኑ ና ደስታዎን ያስጀምሩ!**"
    )
    photo_url = "https://i.ibb.co/8Dt8G2Ps/5930522196038061317-120.jpg"
    
    try:
        bot.send_photo(message.chat.id, photo_url, caption=welcome_text, reply_markup=main_markup())
    except:
        bot.send_message(message.chat.id, welcome_text, reply_markup=main_markup())

    # ለአድሚን ብቻ የሚመጣው መቆጣጠሪያ
    if user_id == ADMIN_ID:
        admin_kb = types.InlineKeyboardMarkup(row_width=1)
        admin_kb.add(
            types.InlineKeyboardButton("📊 Bot Statics", callback_data="admin_stats"),
            types.InlineKeyboardButton("📂 Upload Movies", callback_data="admin_upload"),
            types.InlineKeyboardButton("⚙️ Manage Movies", callback_data="admin_manage")
        )
        bot.send_message(message.chat.id, "🛠 **Admin Control Panel:**", reply_markup=admin_kb)

# --- 6. ADMIN CALLBACKS (STATICS, UPLOAD, MANAGE) ---
@bot.callback_query_handler(func=lambda c: c.data.startswith("admin_"))
def handle_admin_callbacks(call):
    if call.data == "admin_stats":
        c = db_conn.cursor()
        u_count = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        m_count = c.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
        bot.answer_callback_query(call.id, f"📊 ተጠቃሚዎች: {u_count} | 🎬 ፊልሞች: {m_count}", show_alert=True)
    
    elif call.data == "admin_upload":
        msg = bot.send_message(ADMIN_ID, "📂 **ቪዲዮውን ይላኩ (Caption ላይ ስሙን ይጻፉ)...**")
        bot.register_next_step_handler(msg, process_video_upload)
    
    elif call.data == "admin_manage":
        movies = db_conn.execute("SELECT id, name FROM movies ORDER BY id DESC LIMIT 15").fetchall()
        if not movies:
            bot.answer_callback_query(call.id, "ምንም ፊልም የለም!", show_alert=True)
            return
        markup = types.InlineKeyboardMarkup()
        for m_id, m_name in movies:
            markup.add(types.InlineKeyboardButton(f"❌ {m_name}", callback_data=f"del_{m_id}"))
        bot.send_message(ADMIN_ID, "⚙️ **ለማጥፋት የሚፈልጉትን ፊልም ይጫኑ፦**", reply_markup=markup)

# --- 7. UPLOAD PROCESS ---
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
def finalize_upload(call):
    _, icon, price = call.data.split("_")
    data = user_states.get(ADMIN_ID)
    if data:
        db_conn.execute("INSERT INTO movies (name, file_id, price, category) VALUES (?, ?, ?, ?)", (data['name'], data['f_id'], float(price), icon))
        db_conn.commit()
        bot.edit_message_text(f"✅ **{data['name']}** በትክክል ተጭኗል!", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda c: c.data.startswith("del_"))
def delete_movie_exec(call):
    m_id = call.data.split("_")[1]
    db_conn.execute("DELETE FROM movies WHERE id = ?", (m_id,))
    db_conn.commit()
    bot.edit_message_text("✅ ፊልሙ ተሰርዟል!", call.message.chat.id, call.message.message_id)

# --- 8. TEXT HANDLERS (USER BUTTONS) ---
@bot.message_handler(func=lambda m: True)
def handle_text(message):
    text = message.text
    user_id = message.from_user.id

    if text == "※ ጎደኛዬን ልጋብዝ!":
        ref_link = f"https://t.me/ABRSHMovies_Bot?start=ref{user_id}"
        invite_msg = (
            "**ጓደኞችዎን ይጋብዙ ና ሽልማቶች ያግኙ! 🎉**\n\n"
            "**የአብርሽን ፊልሞች እየኮመኮሙ እንዲደሰቱ ጓደኞችዎን ይጋብዙ!**\n\n"
            "**1 ሰው ሲጋብዙ > 0.7 ብር ያገኛሉ!**\n"
            "**ከታች ያለውን ልዩ የግብዣ ሊንክዎን ለጓደኞችዎ ያጋሩ ።**\n\n"
            f"{ref_link}"
        )
        bot.send_message(message.chat.id, invite_msg)

    elif text == "※ አጠቃቀም!":
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

    elif text == "※ ያለኝ ሂሳብ!":
        res = db_conn.execute("SELECT balance FROM users WHERE user_id=?", (user_id,)).fetchone()
        bot.send_message(message.chat.id, f"**⨳ ቀሪ ሂሳብ ~> {res[0] if res else 0.0} ብር**")

    elif text == "※ DM ABRSH!":
        bot.send_message(message.chat.id, "**የዚህ ቦት Owner👉 @ABRSHFILMBET**")

    elif text == "※ ፊልም ልይ!":
        msg = bot.send_message(message.chat.id, "⨳ **የሚፈልጉትን ፊልም ስም ይፃፉ!**")
        bot.register_next_step_handler(msg, process_movie_search)

# --- 9. SEARCH LOGIC ---
def process_movie_search(message):
    query = message.text
    res = db_conn.execute("SELECT id, name, category, price FROM movies WHERE name LIKE ?", (f'%{query}%',)).fetchall()
    if not res:
        bot.send_message(message.chat.id, "⨳ **በዚ ስም የተሰየመ ፊልም ማግኘት አልቻልኩም!**\n⨳ **ፊደል ተሳስተው እንዳይሆን ያረጋግጡ!**")
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for r in res[:10]:
        markup.add(types.InlineKeyboardButton(f"{r[2]} {r[1]} - {r[3]} ብር", callback_data=f"buy_{r[0]}"))
    bot.send_message(message.chat.id, f"🔍 **ውጤቶች ለ '{query}'**", reply_markup=markup)

if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.polling(none_stop=True)
