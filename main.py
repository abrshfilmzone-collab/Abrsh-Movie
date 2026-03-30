import os
import telebot
from telebot import types
import sqlite3
from flask import Flask
from threading import Thread

# --- 1. RENDER SERVER SETUP (DEPLOY እንዳይከሽፍ) ---
app = Flask(__name__)
@app.route('/')
def home(): return "ABRSH MOVIE BOT IS LIVE"
def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

# --- 2. BOT CONFIGURATION ---
TOKEN = "8673546825:AAG3tqrnD_STYgf5gtyjVdbw8awXUQD1m10"
ADMIN_ID = 7908276494 
bot = telebot.TeleBot(TOKEN)

# --- 3. DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('abrsh_cinema_pro.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS movies 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, file_id TEXT, price REAL, category TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 10.0)''')
    conn.commit()
    return conn

conn = init_db()
user_states = {}

# --- 4. KEYBOARDS (ያልጎደለ ሙሉ 8 በተኖች) ---
def main_markup(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("※ ፊልም ልይ!", "※ ያለኝ ሂሳብ!")
    markup.row("※ ገቢ ላድርግ!", "※ ጎደኛዬን ልጋብዝ!")
    markup.row("※ አጠቃቀም!", "※ DM ABRSH!")
    if user_id == ADMIN_ID:
        markup.row("📊 Bot Statics", "📂 Upload Movies")
        markup.row("⚙️ Manage Movies")
    return markup

# --- 5. START HANDLER (ትክክለኛ WELCOME MESSAGE) ---
@bot.message_handler(commands=['start'])
def start(message):
    welcome_text = (
        "※ ሰላም ይህ የ ABRSH Movies Bot ነው እንኳን በደህና መጡ!\n\n"
        "※ በትረጉም ፊልሞቻችን ይዝናኑ!\n\n"
        "※ ፊልም ልይ'ን ይጫኑ ና ደስታዎን ያስጀምሩ!"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=main_markup(message.from_user.id))

# --- 🎬 SMART SEARCH (በትክክል የሚፈልግ) ---
@bot.message_handler(func=lambda m: m.text == "※ ፊልም ልይ!")
def search_start(message):
    msg = bot.send_message(message.chat.id, "🔍 መመልከት የሚፈልጉትን የፊልም ስም ይጻፉ...")
    bot.register_next_step_handler(msg, perform_search)

def perform_search(message):
    query = message.text
    c = conn.cursor()
    # ስሙ በከፊል ቢጻፍም እንዲያገኝ LIKE % % ጥቅም ላይ ውሏል
    c.execute("SELECT id, name, category, price FROM movies WHERE name LIKE ?", (f'%{query}%',))
    results = c.fetchall()

    if not results:
        bot.send_message(message.chat.id, "❌ ይቅርታ፣ ያፈለጉት ፊልም አልተገኘም። እባክዎ ስሙን አስተካክለው ይሞክሩ።")
        return

    markup = types.InlineKeyboardMarkup(row_width=2)
    for r in results:
        # ፊልሙን በከለሩ እና በዋጋው መልክ ያሳያል
        btn_text = f"{r[2]} {r[1]} ({r[3]} ብር)"
        markup.insert(types.InlineKeyboardButton(btn_text, callback_data=f"buy_{r[0]}"))
    
    bot.send_message(message.chat.id, f"🔍 ለ '{query}' የተገኙ ውጤቶች፦", reply_markup=markup)

# --- 📂 ADMIN: UPLOAD WITH COLOR/PRICE ---
@bot.message_handler(func=lambda m: m.text == "📂 Upload Movies" and m.from_user.id == ADMIN_ID)
def admin_upload(message):
    msg = bot.send_message(ADMIN_ID, "📂 ፋይል ወይም ቪዲዮ ይላኩ (Caption ላይ ስሙን ይጻፉ)...")
    bot.register_next_step_handler(msg, process_upload)

def process_upload(message):
    if not message.document and not message.video:
        bot.send_message(ADMIN_ID, "❌ እባክዎ ፋይል ወይም ቪዲዮ ብቻ ይላኩ!")
        return
    
    f_id = message.document.file_id if message.document else message.video.file_id
    f_name = message.caption if message.caption else "ያልተሰየመ ፊልም"
    user_states[ADMIN_ID] = {'f_id': f_id, 'name': f_name}

    markup = types.InlineKeyboardMarkup()
    # በከለር እና በዋጋ ምርጫ
    markup.add(types.InlineKeyboardButton("⚫️ ሲንግል (0.5 ብር)", callback_data="set_⚫️_0.5"),
               types.InlineKeyboardButton("🟡 ተከታታይ (0.3 ብር)", callback_data="set_🟡_0.3"),
               types.InlineKeyboardButton("🔵 አማርኛ (0.5 ብር)", callback_data="set_🔵_0.5"))
    bot.send_message(ADMIN_ID, f"🎬 የፊልም ስም፦ {f_name}\nዋጋ እና አይነት ይምረጡ፦", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("set_"))
def save_movie_data(call):
    _, emoji, price = call.data.split("_")
    data = user_states.get(ADMIN_ID)
    if not data: return
    c = conn.cursor()
    c.execute("INSERT INTO movies (name, file_id, price, category) VALUES (?, ?, ?, ?)",
              (data['name'], data['f_id'], float(price), emoji))
    conn.commit()
    bot.edit_message_text(f"✅ {data['name']} በ {emoji} ስር ተመዝግቧል!", call.message.chat.id, call.message.message_id)

# --- ⚙️ ADMIN: MANAGE MOVIES (ፊልም ለማጥፋት) ---
@bot.message_handler(func=lambda m: m.text == "⚙️ Manage Movies" and m.from_user.id == ADMIN_ID)
def manage_movies(message):
    c = conn.cursor()
    c.execute("SELECT id, name, category FROM movies ORDER BY id DESC LIMIT 15")
    movies = c.fetchall()
    
    if not movies:
        bot.send_message(ADMIN_ID, "ምንም ፊልም የለም።")
        return

    markup = types.InlineKeyboardMarkup()
    for m in movies:
        markup.add(types.InlineKeyboardButton(f"🗑 {m[2]} {m[1]}", callback_data=f"del_{m[0]}"))
    bot.send_message(ADMIN_ID, "ለማጥፋት የሚፈልጉትን ፊልም ይጫኑ፦", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("del_"))
def delete_movie_call(call):
    m_id = call.data.split("_")[1]
    c = conn.cursor()
    c.execute("DELETE FROM movies WHERE id=?", (m_id,))
    conn.commit()
    bot.answer_callback_query(call.id, "✅ ፊልሙ በትክክል ጠፍቷል!")
    manage_movies(call.message)

# --- START BOT & SERVER ---
if __name__ == "__main__":
    Thread(target=run_flask).start()
    print("ABRSH BOT STARTED SUCCESSFULLY!")
    bot.polling(none_stop=True)
