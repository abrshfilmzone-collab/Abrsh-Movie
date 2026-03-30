import os
import telebot
from telebot import types
import sqlite3
import math
from flask import Flask
from threading import Thread

# --- 1. RENDER PORT SETUP ---
app = Flask(__name__)
@app.route('/')
def home(): return "ABRSH BOT IS LIVE!"
def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

# --- 2. BOT CONFIGURATION ---
TOKEN = "8673546825:AAG3tqrnD_STYgf5gtyjVdbw8awXUQD1m10"
ADMIN_ID = 7908276494 
bot = telebot.TeleBot(TOKEN)

# --- 3. DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('abrsh_final.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 10.0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS movies 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, file_id TEXT, price REAL, category TEXT, f_type TEXT)''')
    conn.commit()
    return conn

conn = init_db()
user_states = {}

# --- 4. KEYBOARDS ---
def main_markup(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("※ ፊልም ልይ!", "※ ያለኝ ሂሳብ!")
    markup.row("※ ገቢ ላድርግ!", "※ ጎደኛዬን ልጋብዝ!")
    markup.row("※ አጠቃቀም!", "※ DM ABRSH!")
    if user_id == ADMIN_ID:
        markup.row("📊 Bot Statics", "📂 Upload Movies")
        markup.row("⚙️ Manage Movies")
    return markup

# --- 5. START HANDLER ---
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    bot.send_message(message.chat.id, "⨳ ሰላም ይሄ የABRSH Movies Bot ነው እንኳን በደህና መጡ!\n\n⨳ እባኮ በተኖቹን በመጠቀም ይዘዙኝ!", reply_markup=main_markup(user_id))

# --- 🎬 SEARCH LOGIC (Smart & Pagination) ---
@bot.message_handler(func=lambda m: m.text == "※ ፊልም ልይ!")
def search_start(message):
    msg = bot.send_message(message.chat.id, "🔍 ማየት የሚፈልጉትን የፊልም ስም ይንገሩኝ (ለምሳሌ፡ Spider Man)")
    bot.register_next_step_handler(msg, process_search)

def process_search(message, page=1):
    query = message.text if hasattr(message, 'text') else user_states.get(message.chat.id, {}).get('last_query', '')
    user_states[message.chat.id] = {'last_query': query, 'page': page}
    
    c = conn.cursor()
    # በትክክል እንዲፈልግ LIKE % ይጠቀማል
    c.execute("SELECT name, price, id, category FROM movies WHERE name LIKE ?", (f'%{query}%',))
    results = c.fetchall()
    
    if not results:
        bot.send_message(message.chat.id, "❌ ይቅርታ፣ ያፈለጉት ፊልም አልተገኘም። እባክዎ ስሙን አስተካክለው ይሞክሩ።")
        return

    items_per_page = 4
    total_pages = math.ceil(len(results) / items_per_page)
    start_idx = (page - 1) * items_per_page
    current_items = results[start_idx : start_idx + items_per_page]

    markup = types.InlineKeyboardMarkup(row_width=2)
    for m in current_items:
        markup.insert(types.InlineKeyboardButton(f"{m[3]} {m[0]}", callback_data=f"buy_{m[2]}"))

    nav_btns = []
    if page > 1: nav_btns.append(types.InlineKeyboardButton("⬅️ Back", callback_data=f"page_{page-1}"))
    nav_btns.append(types.InlineKeyboardButton(f"{page}/{total_pages}", callback_data="none"))
    if page < total_pages: nav_btns.append(types.InlineKeyboardButton("Next ➡️", callback_data=f"page_{page+1}"))
    
    markup.row(*nav_btns)
    markup.row(types.InlineKeyboardButton("🔍 New Search", callback_data="new_search"),
               types.InlineKeyboardButton("🏠 Home", callback_data="go_home"))

    text = f"🔍 ለ '{query}' የተገኙ ውጤቶች፦"
    if hasattr(message, 'message_id'):
        bot.edit_message_text(text, message.chat.id, message.message_id, reply_markup=markup)
    else:
        bot.send_message(message.chat.id, text, reply_markup=markup)

# --- 📂 ADMIN: UPLOAD WITH COLOR/CATEGORY ---
@bot.message_handler(func=lambda m: m.text == "📂 Upload Movies" and m.from_user.id == ADMIN_ID)
def upload_init(message):
    msg = bot.send_message(ADMIN_ID, "📤 ቪዲዮውን ወይም ፋይሉን ይላኩ (Caption ላይ ስሙን ይጻፉ)...")
    bot.register_next_step_handler(msg, handle_file_upload)

def handle_file_upload(message):
    if message.content_type not in ['document', 'video']:
        bot.send_message(ADMIN_ID, "❌ እባክዎ ፋይል ወይም ቪዲዮ ብቻ ይላኩ!")
        return
    
    f_id = message.document.file_id if message.content_type == 'document' else message.video.file_id
    f_name = message.caption if message.caption else "ያልተሰየመ ፊልም"
    user_states[ADMIN_ID] = {'temp_fid': f_id, 'temp_name': f_name, 'temp_type': message.content_type}
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("⚫️ ትርጉም ሲንግል (0.5 ብር)", callback_data="cat_⚫️_0.5"),
        types.InlineKeyboardButton("🟡 ትርጉም ተከታታይ (0.3 ብር)", callback_data="cat_🟡_0.3"),
        types.InlineKeyboardButton("🔵 አማርኛ (0.5 ብር)", callback_data="cat_🔵_0.5"),
        types.InlineKeyboardButton("🔴 ኢሮቲክ (1.0 ብር)", callback_data="cat_🔴_1.0"),
        types.InlineKeyboardButton("⚪️ መፅሀፍት (5.0 ብር)", callback_data="cat_⚪️_5.0")
    )
    bot.send_message(ADMIN_ID, f"🎬 ፊልም፦ {f_name}\nእባክዎ የፊልሙን አይነት (ከለር) ይምረጡ፦", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("cat_"))
def save_movie(call):
    _, emoji, price = call.data.split("_")
    data = user_states.get(ADMIN_ID)
    if not data: return
    
    c = conn.cursor()
    c.execute("INSERT INTO movies (name, file_id, price, category, f_type) VALUES (?, ?, ?, ?, ?)",
              (data['temp_name'], data['temp_fid'], float(price), emoji, data['temp_type']))
    conn.commit()
    bot.edit_message_text(f"✅ {data['temp_name']} በ {emoji} ስር ተመዝግቧል!", call.message.chat.id, call.message.message_id)

# --- ⚙️ ADMIN: MANAGE MOVIES ---
@bot.message_handler(func=lambda m: m.text == "⚙️ Manage Movies" and m.from_user.id == ADMIN_ID)
def manage_list(message):
    c = conn.cursor()
    c.execute("SELECT id, name, category FROM movies ORDER BY id DESC LIMIT 10")
    movies = c.fetchall()
    if not movies:
        bot.send_message(ADMIN_ID, "ምንም የተመዘገበ ፊልም የለም።")
        return
    
    markup = types.InlineKeyboardMarkup()
    for m in movies:
        markup.row(types.InlineKeyboardButton(f"🗑 {m[2]} {m[1]}", callback_data=f"del_{m[0]}"))
    bot.send_message(ADMIN_ID, "ለማጥፋት የሚፈልጉትን ፊልም ይጫኑ፦", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("del_"))
def delete_movie_call(call):
    mid = call.data.split("_")[1]
    c = conn.cursor()
    c.execute("DELETE FROM movies WHERE id=?", (mid,))
    conn.commit()
    bot.answer_callback_query(call.id, "✅ ፊልሙ ጠፍቷል!")
    manage_list(call.message)

# --- 🔄 CALLBACK HANDLERS (Pagination & Others) ---
@bot.callback_query_handler(func=lambda call: True)
def handle_all_callbacks(call):
    if call.data.startswith("page_"):
        page = int(call.data.split("_")[1])
        process_search(call.message, page)
    elif call.data == "new_search":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        search_start(call.message)
    elif call.data == "go_home":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        start(call.message)
    elif call.data.startswith("buy_"):
        # እዚህ ጋር የሽያጭ ኮድህን ጨምር (ቀሪ ሂሳብ እያረጋገጠ የሚልክ)
        bot.answer_callback_query(call.id, "ይህ ፊልም ለመግዛት በቂ ሂሳብ ያስፈልግዎታል!", show_alert=True)

# --- 📊 STATICS ---
@bot.message_handler(func=lambda m: m.text == "📊 Bot Statics" and m.from_user.id == ADMIN_ID)
def show_stats(message):
    c = conn.cursor()
    u = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    m = c.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
    bot.send_message(ADMIN_ID, f"📊 **Bot Status**\n\n👥 ጠቅላላ ተጠቃሚዎች: {u}\n🎬 ጠቅላላ ፊልሞች: {m}")

# --- 6. RUN BOT ---
if __name__ == "__main__":
    Thread(target=run_flask).start()
    print("ABRSH BOT IS STARTING...")
    bot.polling(none_stop=True)
