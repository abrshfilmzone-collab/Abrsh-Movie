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
def home(): return "ABRSH MOVIE BOT IS LIVE"
def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

# --- 2. BOT CONFIGURATION ---
TOKEN = "8673546825:AAG3tqrnD_STYgf5gtyjVdbw8awXUQD1m10"
ADMIN_ID = 7908276494 
bot = telebot.TeleBot(TOKEN, parse_mode="Markdown")

# --- 3. DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('abrsh_cinema_pro.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 5.0)')
    c.execute('CREATE TABLE IF NOT EXISTS movies (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, file_id TEXT, price REAL, category TEXT)')
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
        markup.row("📊 Bot Statics", "📂 Upload Movies", "⚙️ Manage Movies")
    return markup

# --- 5. START & REFERRAL LOGIC ---
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    args = message.text.split()
    
    c = conn.cursor()
    user_exists = c.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,)).fetchone()
    
    if not user_exists:
        c.execute("INSERT INTO users (user_id, balance) VALUES (?, ?)", (user_id, 5.0))
        if len(args) > 1 and args[1].startswith("ref"):
            ref_id = args[1].replace("ref", "")
            try:
                ref_id = int(ref_id)
                if ref_id != user_id:
                    c.execute("UPDATE users SET balance = balance + 0.7 WHERE user_id = ?", (ref_id,))
                    bot.send_message(ref_id, "🎉 **አንድ ሰው ስለጋበዙ 0.7 ብር ወደ ሂሳብዎ ተጨምሯል!**")
            except: pass
        conn.commit()

    welcome_text = (
        "**※ ሰላም ይህ የ ABRSH Movies Bot ነው እንኳን በደህና መጡ!**\n\n"
        "**※ በትረጉም ፊልሞቻችን ይዝናኑ!**\n\n"
        "**※ ፊልም ልይ'ን ይጫኑ ና ደስታዎን ያስጀምሩ!**"
    )
    photo = "https://i.ibb.co/8Dt8G2Ps/5930522196038061317-120.jpg"
    try: bot.send_photo(message.chat.id, photo, caption=welcome_text, reply_markup=main_markup(user_id))
    except: bot.send_message(message.chat.id, welcome_text, reply_markup=main_markup(user_id))

# --- 6. SEARCH & PAGINATION ---
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
        bot.send_message(message.chat.id, f"❌ **ይቅርታ፣ ለ '{query}' የተገኘ ፊልም የለም።**")
        return

    total_p = math.ceil(len(res) / 10)
    items = res[(page-1)*10 : page*10]
    markup = types.InlineKeyboardMarkup(row_width=1)
    for r in items: markup.add(types.InlineKeyboardButton(f"{r[2]} {r[1]} - {r[3]} ብር", callback_data=f"buy_{r[0]}"))
    
    nav = []
    if page > 1: nav.append(types.InlineKeyboardButton("⬅️ Back", callback_data=f"p_{page-1}"))
    if page < total_p: nav.append(types.InlineKeyboardButton("Next ➡️", callback_data=f"p_{page+1}"))
    if nav: markup.row(*nav)
    markup.row(types.InlineKeyboardButton("🔍 New Search", callback_data="n_s"), types.InlineKeyboardButton("🏠 Home", callback_data="h_m"))
    
    text = f"🔍 **ውጤቶች ለ '{query}' (ገጽ {page}/{total_p})**"
    if hasattr(message, 'message_id') and message.from_user.is_bot: bot.edit_message_text(text, message.chat.id, message.message_id, reply_markup=markup)
    else: bot.send_message(message.chat.id, text, reply_markup=markup)

# --- 7. DEPOSIT SYSTEM ---
@bot.message_handler(func=lambda m: m.text == "※ ገቢ ላድርግ!")
def dep_start(message):
    kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("Telebirr", callback_data="t_b"))
    bot.send_message(message.chat.id, "⨳ **ገቢ የሚያደርጉበት መንገድ ቴሌብር ነው!**", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "t_b")
def t_b_info(call):
    txt = "**ምን ያህል ብር ማስገባት ይፈልጋሉ?**\nክፍያ በTelebirr ነው።\n\nትንሹ: 5 ብር | ትልቁ: 1,000 ብር\n\n⨳በዚህ `+251961343796` በቴሌብር በማስገባት **Screen Shoot** ላኩ።"
    bot.edit_message_text(txt, call.message.chat.id, call.message.message_id)
    bot.register_next_step_handler(call.message, wait_ss)

def wait_ss(message):
    if message.content_type != 'photo': return bot.send_message(message.chat.id, "❌ እባክዎ ፎቶ ይላኩ!")
    kb = types.InlineKeyboardMarkup().row(types.InlineKeyboardButton("✅ Accept", callback_data=f"a_{message.from_user.id}"), types.InlineKeyboardButton("❌ Reject", callback_data=f"r_{message.from_user.id}"))
    bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=f"📩 **ክፍያ ከ {message.from_user.id}**", reply_markup=kb)
    bot.send_message(message.chat.id, "✅ **Screen Shoot ተልኳል!**")

# --- 8. OTHER BUTTONS ---
@bot.message_handler(func=lambda m: True)
def other_btns(m):
    if m.text == "※ ያለኝ ሂሳብ!":
        res = conn.execute("SELECT balance FROM users WHERE user_id=?", (m.from_user.id,)).fetchone()
        bot.send_message(m.chat.id, f"**⨳ ቀሪ ሂሳብ ~> {res[0] if res else 0.0} ብር**")
    elif m.text == "※ DM ABRSH!":
        bot.send_message(m.chat.id, "**የዚህ ቦት Owner👉 @ABRSHFILMBET**")
    elif m.text == "※ አጠቃቀም!":
        txt = "🧶 **የICON ከለሮች ትርጉም**\n\">\">\">\">\">\">\">\">\n⚫️-ትርጉም | 🟢-ሲንግል | 🟡-ተከታታይ | 🔴-ሮማንስ | 🔵-አማርኛ | 🟣-ተከታታይ አማርኛ | 🟠-ቃና | ⚪️-መፅሀፍት\n\">\">\">\">\">\">\">\">\n💰ሲንግል:0.5 | ተከታታይ:0.3 | አማርኛ:0.5 | ኢሮቲክ:1 | ቃና:0.3 | መፅሀፍ:5\n\">\">\">\">\">\">\">\">\n✅ @ABRSHFILMBET"
        bot.send_message(m.chat.id, txt)
    elif m.text == "※ ጎደኛዬን ልጋብዝ!":
        link = f"https://t.me/ABRSHMovies_Bot?start=ref{m.from_user.id}"
        bot.send_message(m.chat.id, f"**ጓደኞችዎን ይጋብዙ!**\n\n1 ሰው ሲጋብዙ > 0.7 ብር ያገኛሉ!\n\nሊንክዎ፦ {link}")

# --- 9. CALLBACKS ---
@bot.callback_query_handler(func=lambda c: True)
def calls(c):
    if c.data.startswith("p_"): process_search(c.message, int(c.data.split("_")[1]))
    elif c.data == "n_s": bot.delete_message(c.message.chat.id, c.message.message_id); search_init(c.message)
    elif c.data == "h_m": bot.delete_message(c.message.chat.id, c.message.message_id); bot.send_message(c.message.chat.id, "⨳ **እባኮ በተኖቹን በመጠቀም ይዘዙኝ!**", reply_markup=main_markup(c.from_user.id))
    elif c.data.startswith("a_"):
        u_id = c.data.split("_")[1]
        msg = bot.send_message(ADMIN_ID, f"💰 **ለ {u_id} የሚገባ ብር?**")
        bot.register_next_step_handler(msg, lambda m: add_bal(m, u_id))
    elif c.data.startswith("buy_"):
        m_id = c.data.split("_")[1]
        m = conn.execute("SELECT name, file_id, price FROM movies WHERE id=?", (m_id,)).fetchone()
        u = conn.execute("SELECT balance FROM users WHERE user_id=?", (c.from_user.id,)).fetchone()
        if u[0] >= m[2]:
            conn.execute("UPDATE users SET balance=balance-? WHERE user_id=?", (m[2], c.from_user.id)); conn.commit()
            bot.send_document(c.from_user.id, m[1], caption=f"✅ **{m[0]}**")
        else: bot.answer_callback_query(c.id, "❌ በቂ ሂሳብ የለዎትም!", show_alert=True)

def add_bal(m, u_id):
    try:
        conn.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (float(m.text), u_id)); conn.commit()
        bot.send_message(u_id, f"✅ **{m.text} ብር ገቢ ሆኗል!**")
    except: pass

if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.polling(none_stop=True)
