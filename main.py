import telebot
from telebot import types
import sqlite3

# --- 1. CONFIGURATION ---
# አዲሱ ቶከን ተተክቷል
TOKEN = "8673546825:AAG3tqrnD_STYgf5gtyjVdbw8awXUQD1m10"
ADMIN_ID = 7908276494 
PHOTO_URL = "https://i.ibb.co/PsQG4KDY/IMG-20260329-190151-356.jpg"
bot = telebot.TeleBot(TOKEN)

# --- 2. DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('abrsh_final.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 10.0, invited_by INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS movies
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, file_id TEXT, price REAL, f_type TEXT)''')
    conn.commit()
    return conn

conn = init_db()
temp_data = {} 

# --- 3. KEYBOARDS ---
def main_markup(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("⨳ ፊልም ልይ!", "⨳ ያለኝ ሂሳብ!")
    markup.row("⨳ ገቢ ላድርግ!", "⨳ ጎደኛዬን ልጋብዝ!")
    markup.row("⨳ አጠቃቀም!", "※ DM ABRSH!")
    if user_id == ADMIN_ID:
        markup.row("📂 Upload Movies")
    return markup

# --- 4. START ---
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    if not c.fetchone():
        c.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
    
    welcome = "⨳ ሰላም ይሄ የABRSH Movies Bot ነው እንኳን በደህና መጡ!"
    bot.send_photo(message.chat.id, PHOTO_URL, caption=welcome, reply_markup=main_markup(user_id))

# --- 📂 ADMIN: UPLOAD (ቪዲዮም ይሁን ፋይል ይቀበላል) ---
@bot.message_handler(func=lambda m: m.text == "📂 Upload Movies" and m.from_user.id == ADMIN_ID)
def ask_for_file(message):
    msg = bot.send_message(message.chat.id, "📤 Send Me File/Video Sir (ፋይሉን ወይም ቪዲዮውን ይላኩ)")
    bot.register_next_step_handler(msg, save_media_step)

def save_media_step(message):
    f_id, f_name, f_type = None, None, None

    if message.content_type == 'document':
        f_id, f_type = message.document.file_id, 'doc'
        f_name = message.caption if message.caption else message.document.file_name
    elif message.content_type == 'video':
        f_id, f_type = message.video.file_id, 'vid'
        f_name = message.caption if message.caption else "ያልተሰየመ ፊልም"
    else:
        bot.send_message(ADMIN_ID, "❌ እባክዎ ፋይል ወይም ቪዲዮ ብቻ ይላኩ!")
        return

    temp_data[ADMIN_ID] = {"id": f_id, "name": f_name, "type": f_type}
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⚫️ ሲንግል (0.5 ብር)", callback_data="p_0.5"),
               types.InlineKeyboardButton("🟡 ተከታታይ (0.3 ብር)", callback_data="p_0.3"))
    markup.add(types.InlineKeyboardButton("🔵 አማርኛ (0.5 ብር)", callback_data="p_0.5"),
               types.InlineKeyboardButton("🔴 ኢሮቲክ (1.0 ብር)", callback_data="p_1.0"))
    markup.add(types.InlineKeyboardButton("⚪️ መፅሀፍ (5.0 ብር)", callback_data="p_5.0"))
    
    bot.send_message(ADMIN_ID, f"🎬 የተቀበለው፦ {f_name}\nዋጋ ይምረጡ፦", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("p_"))
def final_save(call):
    price = float(call.data.split("_")[1])
    info = temp_data.get(ADMIN_ID)
    if info:
        c = conn.cursor()
        c.execute("INSERT INTO movies (name, file_id, price, f_type) VALUES (?, ?, ?, ?)", 
                  (info['name'], info['id'], price, info['type']))
        conn.commit()
        bot.edit_message_text(f"✅ ተመዝግቧል!\n🎬 {info['name']} - {price} ብር", call.message.chat.id, call.message.message_id)

# --- 🎬 ፊልም ፍለጋ ---
@bot.message_handler(func=lambda m: m.text == "⨳ ፊልም ልይ!")
def search(message):
    msg = bot.send_message(message.chat.id, "⨳ የፊልሙን ስም ይፃፉ...")
    bot.register_next_step_handler(msg, run_search)

def run_search(message):
    c = conn.cursor()
    c.execute("SELECT name, price FROM movies WHERE name LIKE ?", ('%' + message.text + '%',))
    res = c.fetchall()
    if res:
        markup = types.InlineKeyboardMarkup()
        for r in res:
            markup.add(types.InlineKeyboardButton(f"🎬 {r[0]} ({r[1]} ብር)", callback_data=f"buy_{r[0]}"))
        bot.send_message(message.chat.id, "የተገኙ ውጤቶች፦", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "❌ አልተገኘም!")

# --- 🛒 መግዣ ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def buy(call):
    m_name = call.data.replace("buy_", "")
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE user_id=?", (call.from_user.id,))
    bal = c.fetchone()[0]
    c.execute("SELECT file_id, price, f_type FROM movies WHERE name=?", (m_name,))
    m = c.fetchone()
    
    if m and bal >= m[1]:
        c.execute("UPDATE users SET balance = balance - ? WHERE user_id=?", (m[1], call.from_user.id))
        conn.commit()
        if m[2] == 'vid': bot.send_video(call.from_user.id, m[0])
        else: bot.send_document(call.from_user.id, m[0])
    else:
        bot.answer_callback_query(call.id, "⚠️ በቂ ሂሳብ የለዎትም!", show_alert=True)

# --- 💰 ገቢ ላድርግ ---
@bot.message_handler(func=lambda m: m.text == "⨳ ገቢ ላድርግ!")
def deposit(message):
    bot.send_message(message.chat.id, "⨳ በ +251961343796 በቴሌብር ብር ልከው Screenshot ይላኩ!")

@bot.message_handler(content_types=['photo'])
def screen(message):
    if message.chat.id != ADMIN_ID:
        bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ አጽድቅ", callback_data=f"ok_{message.chat.id}"))
        bot.send_message(ADMIN_ID, f"ክፍያ ከ {message.chat.id} ደርሷል", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("ok_"))
def ok(call):
    uid = call.data.split("_")[1]
    msg = bot.send_message(ADMIN_ID, f"💰 ለ {uid} ስንት ብር ይግባ?")
    bot.register_next_step_handler(msg, finish_dep, uid)

def finish_dep(message, uid):
    c = conn.cursor()
    c.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (float(message.text), uid))
    conn.commit()
    bot.send_message(uid, f"🎉 {message.text} ብር ገቢ ሆኗል!")
    bot.send_message(ADMIN_ID, "✅ ተፈፅሟል")

bot.polling(none_stop=True)
