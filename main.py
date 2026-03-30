import telebot
from telebot import types
import sqlite3
import math

# --- 1. CONFIGURATION ---
TOKEN = "8673546825:AAG3tqrnD_STYgf5gtyjVdbw8awXUQD1m10"
ADMIN_ID = 7908276494 
PHOTO_URL = "https://i.ibb.co/PsQG4KDY/IMG-20260329-190151-356.jpg"
bot = telebot.TeleBot(TOKEN)

# --- 2. DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('abrsh_final.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 10.0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS movies 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, file_id TEXT, price REAL, f_type TEXT)''')
    conn.commit()
    return conn

conn = init_db()
user_states = {} 

# --- 3. KEYBOARDS (Main Menu with Emojis) ---
def main_markup(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("※ ፊልም ልይ!", "※ ያለኝ ሂሳብ!")
    markup.row("※ ገቢ ላድርግ!", "※ ጎደኛዬን ልጋብዝ!")
    markup.row("※ አጠቃቀም!", "※ DM ABRSH!")
    if user_id == ADMIN_ID:
        markup.row("📊 Bot Statics", "📂 Upload Movies")
        markup.row("⚙️ Manage Movies")
    return markup

# --- 4. START ---
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    welcome = "⨳ ሰላም ይሄ የABRSH Movies Bot ነው እንኳን በደህና መጡ!\n\n⨳ እባኮ በተኖቹን በመጠቀም ይዘዙኝ!"
    bot.send_photo(message.chat.id, PHOTO_URL, caption=welcome, reply_markup=main_markup(user_id))

# --- 📊 ADMIN: STATICS ---
@bot.message_handler(func=lambda m: m.text == "📊 Bot Statics" and m.from_user.id == ADMIN_ID)
def bot_statics(message):
    c = conn.cursor()
    u_count = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    m_count = c.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
    bot.send_message(message.chat.id, f"📈 **ABRSH Account Statics**\n\n👥 ጠቅላላ ተጠቃሚዎች: {u_count}\n🎬 ጠቅላላ ፊልሞች: {m_count}", parse_mode="Markdown")

# --- 🎬 SEARCH & PAGINATION (With Emojis) ---
@bot.message_handler(func=lambda m: m.text == "※ ፊልም ልይ!")
def search_init(message):
    msg = bot.send_message(message.chat.id, "※ ማየት የሚፈልጉትን የፊልም ስም ይንገሩኝ::")
    bot.register_next_step_handler(msg, perform_search)

def perform_search(message, page=1):
    query = message.text if hasattr(message, 'text') else user_states.get(message.chat.id, {}).get('query', '')
    user_states[message.chat.id] = {'query': query, 'page': page}
    
    c = conn.cursor()
    c.execute("SELECT name, price, id FROM movies WHERE name LIKE ?", ('%' + query + '%',))
    all_results = c.fetchall()
    
    if not all_results:
        bot.send_message(message.chat.id, "⨳ በዚ ስም የተሰየመ ፊልም ማግኘት አልቻልኩም!")
        return

    items_per_page = 10
    total_pages = math.ceil(len(all_results) / items_per_page)
    start_idx = (page - 1) * items_per_page
    current_items = all_results[start_idx:start_idx + items_per_page]

    markup = types.InlineKeyboardMarkup(row_width=2) 
    btns = [types.InlineKeyboardButton(f"🎬 {item[0]}", callback_data=f"buy_{item[2]}") for item in current_items]
    markup.add(*btns)

    nav_btns = []
    if page > 1: 
        nav_btns.append(types.InlineKeyboardButton("⬅️ Back", callback_data=f"pg_{page-1}"))
    
    nav_btns.append(types.InlineKeyboardButton(f"{page}/{total_pages}", callback_data="none"))
    
    if page < total_pages: 
        nav_btns.append(types.InlineKeyboardButton("Next ➡️", callback_data=f"pg_{page+1}"))
    
    markup.row(*nav_btns)
    # አሁን እዚህ ጋር ኢሞጂዎቹ ተጨምረዋል
    markup.row(types.InlineKeyboardButton("🔍 New Search", callback_data="reset_search"),
               types.InlineKeyboardButton("🏠 Home", callback_data="back_home"))

    text = f"Results for: {query}\nPage {page} of {total_pages}"
    if hasattr(message, 'message_id'):
        bot.edit_message_text(text, message.chat.id, message.message_id, reply_markup=markup)
    else:
        bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("pg_"))
def handle_pg(call):
    page = int(call.data.split("_")[1])
    perform_search(call.message, page)

@bot.callback_query_handler(func=lambda call: call.data == "reset_search")
def reset_search(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    search_init(call.message)

@bot.callback_query_handler(func=lambda call: call.data == "back_home")
def back_home(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, "⨳ እባኮ በተኖቹን በመጠቀም ይዘዙኝ!", reply_markup=main_markup(call.from_user.id))

# --- ⚙️ ADMIN: MANAGE (Edit/Delete) ---
@bot.message_handler(func=lambda m: m.text == "⚙️ Manage Movies" and m.from_user.id == ADMIN_ID)
def manage(message):
    c = conn.cursor()
    movies = c.execute("SELECT id, name FROM movies ORDER BY id DESC LIMIT 10").fetchall()
    markup = types.InlineKeyboardMarkup()
    for m in movies:
        markup.row(types.InlineKeyboardButton(f"🎬 {m[1]}", callback_data=f"mng_{m[0]}"))
    bot.send_message(message.chat.id, "ለማስተካከል ወይም ለማጥፋት ፊልም ይምረጡ፦", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("mng_"))
def mng_opt(call):
    mid = call.data.split("_")[1]
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("🗑 አጥፋ (Delete)", callback_data=f"rm_{mid}"))
    markup.row(types.InlineKeyboardButton("🔄 አይነት ቀይር (Edit)", callback_data=f"ed_{mid}"))
    bot.edit_message_text("ምን ማድረግ ይፈልጋሉ?", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("rm_"))
def rm_mov(call):
    mid = call.data.split("_")[1]
    c = conn.cursor()
    c.execute("DELETE FROM movies WHERE id=?", (mid,))
    conn.commit()
    bot.edit_message_text("✅ ፊልሙ በተሳካ ሁኔታ ጠፍቷል።", call.message.chat.id, call.message.message_id)

# --- 🍿 OLD FUNCTIONS (Upload, Invite, Usage) ---
@bot.message_handler(func=lambda m: m.text == "※ አጠቃቀም!")
def usage_guide(message):
    guide = (
        "🍿 የአብርሽ ፊልም ቤት ቦት አጠቃቀም መመሪያ።\n\n"
        "⚫️ -> ትርጉም ሲንግል (0.5 ብር)\n"
        "🟡 -> ትርጉም ተከታታይ (0.3 ብር)\n"
        "🔵 -> አማርኛ (0.5 ብር)\n"
        "🔴 -> ኢሮቲክ (1 ብር)\n"
        "⚪️ -> መፅሀፍት (5 ብር)\n\n"
        "✅ @ABRSHFILMBET"
    )
    bot.send_message(message.chat.id, guide)

@bot.message_handler(func=lambda m: m.text == "※ ጎደኛዬን ልጋብዝ!")
def invite(message):
    ref_link = f"https://t.me/ABRSHMovies_Bot?start={message.from_user.id}"
    bot.send_message(message.chat.id, f"ጓደኞችዎን ይጋብዙ ና ሽልማቶች ያግኙ! 🎉\n\n1 ሰው ሲጋብዙ > 1 ብር ያገኛሉ!\n\nየግብዣ ሊንክዎ፦\n{ref_link}")

@bot.message_handler(func=lambda m: m.text == "※ ያለኝ ሂሳብ!")
def bal(message):
    c = conn.cursor()
    res = c.execute("SELECT balance FROM users WHERE user_id=?", (message.from_user.id,)).fetchone()
    bot.send_message(message.chat.id, f"⨳ ቀሪ ሂሳብ ~> {res[0] if res else 0.0} ብር።")

@bot.message_handler(func=lambda m: m.text == "📂 Upload Movies" and m.from_user.id == ADMIN_ID)
def up(message):
    msg = bot.send_message(message.chat.id, "📤 ቪዲዮውን ወይም ፋይሉን ይላኩ...")
    bot.register_next_step_handler(msg, save_up)

def save_up(message):
    if message.content_type not in ['document', 'video']: return
    f_id = message.document.file_id if message.content_type == 'document' else message.video.file_id
    f_name = message.caption if message.caption else "ያልተሰየመ"
    user_states[ADMIN_ID] = {'f_id': f_id, 'f_name': f_name, 'f_type': message.content_type}
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⚫️ ሲንግል (0.5)", callback_data="pr_0.5"),
               types.InlineKeyboardButton("🟡 ተከታታይ (0.3)", callback_data="pr_0.3"))
    bot.send_message(ADMIN_ID, f"🎬 የተቀበለው፦ {f_name}\nዋጋ ይምረጡ፦", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("pr_"))
def fin_up(call):
    price = float(call.data.split("_")[1])
    d = user_states.get(ADMIN_ID)
    c = conn.cursor()
    c.execute("INSERT INTO movies (name, file_id, price, f_type) VALUES (?, ?, ?, ?)", (d['f_name'], d['f_id'], price, d['f_type']))
    conn.commit()
    bot.edit_message_text("✅ ተመዝግቧል!", call.message.chat.id, call.message.message_id)

bot.polling(none_stop=True)
