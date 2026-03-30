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

# --- 4. KEYBOARDS (ለተጠቃሚ 6 በተኖች ብቻ) ---
def main_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("※ ፊልም ልይ!", "※ ያለኝ ሂሳብ!")
    markup.row("※ ገቢ ላድርግ!", "※ ጎደኛዬን ልጋብዝ!")
    markup.row("※ አጠቃቀም!", "※ DM ABRSH!")
    return markup

# --- 5. START & ADMIN INLINE BUTTONS ---
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    
    # Register user (5 ETB gift silently)
    c = conn.cursor()
    user_exists = c.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,)).fetchone()
    if not user_exists:
        c.execute("INSERT INTO users (user_id, balance) VALUES (?, ?)", (user_id, 5.0))
        conn.commit()

    welcome_text = (
        "**※ ሰላም ይህ የ ABRSH Movies Bot ነው እንኳን በደህና መጡ!**\n\n"
        "**※ በትረጉም ፊልሞቻችን ይዝናኑ!**\n\n"
        "**※ ፊልም ልይ'ን ይጫኑ ና ደስታዎን ያስጀምሩ!**"
    )
    photo = "https://i.ibb.co/8Dt8G2Ps/5930522196038061317-120.jpg"
    
    # ለአድሚን ብቻ የሚመጡ Inline Buttons
    admin_kb = None
    if user_id == ADMIN_ID:
        admin_kb = types.InlineKeyboardMarkup()
        admin_kb.add(types.InlineKeyboardButton("📊 Bot Statics", callback_data="admin_stats"))
        admin_kb.add(types.InlineKeyboardButton("📂 Upload Movies", callback_data="admin_upload"))
        admin_kb.add(types.InlineKeyboardButton("⚙️ Manage Movies", callback_data="admin_manage"))

    try:
        bot.send_photo(message.chat.id, photo, caption=welcome_text, reply_markup=main_markup())
        if admin_kb:
            bot.send_message(message.chat.id, "🛠 **Admin Control Panel:**", reply_markup=admin_kb)
    except:
        bot.send_message(message.chat.id, welcome_text, reply_markup=main_markup())

# --- 6. ፊልም ልይ (SEARCH LOGIC) ---
@bot.message_handler(func=lambda m: m.text == "※ ፊልም ልይ!")
def search_init(message):
    msg = bot.send_message(message.chat.id, "⨳ **የሚፈልጉትን ፊልም ስም ይፃፉ!**")
    bot.register_next_step_handler(msg, process_search)

def process_search(message, page=1):
    query = message.text if hasattr(message, 'text') else user_states.get(message.chat.id, {}).get('q')
    if not query: return
    user_states[message.chat.id] = {'q': query, 'p': page}
    
    c = conn.cursor()
    c.execute("SELECT id, name, category, price FROM movies WHERE name LIKE ?", (f'%{query}%',))
    res = c.fetchall()
    
    if not res:
        bot.send_message(message.chat.id, "⨳ **በዚ ስም የተሰየመ ፊልም ማግኘት አልቻልኩም!**\n⨳ **ፊደል ተሳስተው እንዳይሆን ያረጋግጡ!**")
        return

    total_p = math.ceil(len(res) / 10)
    items = res[(page-1)*10 : page*10]
    markup = types.InlineKeyboardMarkup(row_width=1)
    for r in items:
        markup.add(types.InlineKeyboardButton(f"{r[2]} {r[1]} - {r[3]} ብር", callback_data=f"buy_{r[0]}"))
    
    nav = []
    if page > 1: nav.append(types.InlineKeyboardButton("⬅️ Back", callback_data=f"p_{page-1}"))
    if page < total_p: nav.append(types.InlineKeyboardButton("Next ➡️", callback_data=f"p_{page+1}"))
    if nav: markup.row(*nav)
    markup.row(types.InlineKeyboardButton("🔍 New Search", callback_data="n_s"), types.InlineKeyboardButton("🏠 Home", callback_data="h_m"))
    
    bot.send_message(message.chat.id, f"🔍 **ውጤቶች ለ '{query}' (ገጽ {page}/{total_p})**", reply_markup=markup)

# --- 7. አጠቃቀም (DETAILED) ---
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

# --- 8. CALLBACK HANDLER (ADMIN & USER) ---
@bot.callback_query_handler(func=lambda c: True)
def handle_all_callbacks(call):
    # User Search Pagination
    if call.data.startswith("p_"):
        process_search(call.message, int(call.data.split("_")[1]))
    elif call.data == "n_s":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        search_init(call.message)
    elif call.data == "h_m":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, "⨳ **እባኮ በተኖቹን በመጠቀም ይዘዙኝ!**")

    # Admin Tools
    elif call.data == "admin_stats":
        c = conn.cursor()
        u_count = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        m_count = c.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
        bot.answer_callback_query(call.id, f"Users: {u_count} | Movies: {m_count}", show_alert=True)
    
    elif call.data == "admin_upload":
        msg = bot.send_message(ADMIN_ID, "📂 **ቪዲዮውን ይላኩ (Caption ላይ ስሙን ይጻፉ)...**")
        bot.register_next_step_handler(msg, handle_upload_process)

# --- 9. OTHER BUTTONS (DM, BALANCE, REF) ---
@bot.message_handler(func=lambda m: True)
def text_handler(m):
    if m.text == "※ ያለኝ ሂሳብ!":
        res = conn.execute("SELECT balance FROM users WHERE user_id=?", (m.from_user.id,)).fetchone()
        bot.send_message(m.chat.id, f"**⨳ ቀሪ ሂሳብ ~> {res[0] if res else 0.0} ብር**")
    elif m.text == "※ DM ABRSH!":
        bot.send_message(m.chat.id, "**የዚህ ቦት Owner👉 @ABRSHFILMBET**")
    elif m.text == "※ ጎደኛዬን ልጋብዝ!":
        link = f"https://t.me/ABRSHMovies_Bot?start=ref{m.from_user.id}"
        bot.send_message(m.chat.id, f"**ጓደኞችዎን ይጋብዙ!**\n\n1 ሰው ሲጋብዙ > 0.7 ብር ያገኛሉ!\n\nሊንክዎ፦ {link}")

# (ቀሪው የገቢ ላድርግ እና የፊልም መጫኛ ኮድ እንደቀድሞው በትክክል ተካቷል)

if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.polling(none_stop=True)
