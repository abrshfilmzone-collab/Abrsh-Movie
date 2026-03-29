import telebot
from telebot import types
import sqlite3

# --- 1. CONFIGURATION ---
TOKEN = "8673546825:AAEB1yHAx-qV03bVdmSF1yKNNct9_iv72x8"
ADMIN_ID = 7908276494 
ADMIN_USERNAME = "@ABRSHFILMBET"
bot = telebot.TeleBot(TOKEN)

# --- 2. DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('abrsh_final.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (user_id INTEGER PRIMARY KEY, balance REAL, invited_by INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS movies 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, file_id TEXT, category TEXT, price REAL)''')
    conn.commit()
    conn.close()

init_db()

def db_query(query, params=(), fetch=False):
    conn = sqlite3.connect('abrsh_final.db', check_same_thread=False)
    c = conn.cursor()
    c.execute(query, params)
    res = c.fetchall() if fetch else None
    conn.commit()
    conn.close()
    return res

# --- 3. START COMMAND ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.chat.id
    user = db_query("SELECT * FROM users WHERE user_id=?", (uid,), fetch=True)
    
    if not user:
        ref_id = None
        if len(message.text.split()) > 1 and "ref_" in message.text:
            ref_id = int(message.text.split()[1].replace("ref_", ""))
            db_query("UPDATE users SET balance = balance + 1 WHERE user_id=?", (ref_id,))
            bot.send_message(ref_id, "🎁 በሪፈራልዎ 1 ሰው ስለገባ 1 ብር ተጨምሮልዎታል!")
        
        db_query("INSERT INTO users VALUES (?, ?, ?)", (uid, 10.0, ref_id))

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("※ ፊልም ልይ!", "※ ያለኝ ሂሳብ!", "※ ገቢ ላድርግ!", "※ ጎደኛዬን ልጋብዝ!", "※ አጠቃቀም!", "※ DM ABRSH")
    
    bot.send_message(uid, "⨳ ሰላም! ወደ ABRSH FILM BET እንኳን በደህና መጡ! 🍿", reply_markup=markup)

# --- 4. MOVIE UPLOAD (ADMIN ONLY) ---
@bot.message_handler(content_types=['video', 'document'])
def handle_upload(message):
    if message.chat.id != ADMIN_ID: return
    f_id = message.video.file_id if message.video else message.document.file_id
    msg = bot.send_message(ADMIN_ID, "ፊልሙ ደርሶኛል! ስሙን ይጻፉ...")
    bot.register_next_step_handler(msg, lambda m: get_name(m, f_id))

def get_name(message, f_id):
    name = message.text
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("ሲንግል (3 ብር)", callback_data=f"save_{f_id}_{name}_3_🟢"),
               types.InlineKeyboardButton("ተከታታይ (2 ብር)", callback_data=f"save_{f_id}_{name}_2_🟡"))
    bot.send_message(ADMIN_ID, f"የ '{name}' ዋጋ ይምረጡ፦", reply_markup=markup)

# --- 5. CALLBACK HANDLER ---
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    d = call.data.split('_')
    if d[0] == "save":
        full_n = f"{d[4]} {d[2]}"
        db_query("INSERT INTO movies (name, file_id, category, price) VALUES (?, ?, ?, ?)", (full_n, d[1], d[4], float(d[3])))
        bot.edit_message_text(f"✅ {full_n} ተመዝግቧል!", call.message.chat.id, call.message.message_id)
    elif d[0] == "buy":
        m = db_query("SELECT * FROM movies WHERE id=?", (int(d[1]),), fetch=True)[0]
        bal = db_query("SELECT balance FROM users WHERE user_id=?", (call.from_user.id,), fetch=True)[0][0]
        if bal >= m[4]:
            db_query("UPDATE users SET balance = balance - ? WHERE user_id=?", (m[4], call.from_user.id))
            bot.send_document(call.from_user.id, m[2], caption=f"{m[1]}\n✅ ተልኳል!")
        else:
            bot.answer_callback_query(call.id, "⚠️ በቂ ሂሳብ የለዎትም!", show_alert=True)

# --- 6. MENU ACTIONS ---
@bot.message_handler(func=lambda m: True)
def menus(message):
    uid = message.chat.id
    if message.text == "※ ያለኝ ሂሳብ!":
        bal = db_query("SELECT balance FROM users WHERE user_id=?", (uid,), fetch=True)[0][0]
        bot.send_message(uid, f"💰 ቀሪ ሂሳብዎ፦ {bal} ብር")
    elif message.text == "※ ፊልም ልይ!":
        msg = bot.send_message(uid, "የፊልም ስም ይጻፉ...")
        bot.register_next_step_handler(msg, search)
    elif message.text == "※ ጎደኛዬን ልጋብዝ!":
        bot.send_message(uid, f"የእርስዎ ሊንክ፦ https://t.me/ABRSHMovies_Bot?start=ref_{uid}")
    elif message.text == "※ DM ABRSH":
        bot.send_message(uid, f"አስተዳዳሪ፡ {ADMIN_USERNAME}")

def search(message):
    res = db_query("SELECT * FROM movies WHERE name LIKE ?", (f"%{message.text}%",), fetch=True)
    if res:
        for m in res:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(f"ግዛ ({m[4]} ብር)", callback_data=f"buy_{m[0]}"))
            bot.send_message(message.chat.id, m[1], reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "⚠️ አልተገኘም!")

bot.polling(none_stop=True)
