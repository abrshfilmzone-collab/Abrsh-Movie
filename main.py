import telebot
from telebot import types
import sqlite3

# --- 1. CONFIGURATION ---
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
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, file_id TEXT, price REAL, file_type TEXT)''')
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

# --- 4. START COMMAND ---
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    args = message.text.split()
    referrer = int(args[1]) if len(args) > 1 else None
    
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    if not c.fetchone():
        c.execute("INSERT INTO users (user_id, invited_by) VALUES (?, ?)", (user_id, referrer))
        conn.commit()
        if referrer:
            c.execute("UPDATE users SET balance = balance + 1.0 WHERE user_id=?", (referrer,))
            conn.commit()
            bot.send_message(referrer, "🎉 እንኳን ደስ አለዎት! በግብዣዎ ምክንያት 1.0 ብር ተጨምሯል።")

    welcome_text = "⨳ ሰላም ይሄ የABRSH Movies Bot ነው እንኳን በደህና መጡ!\n\n⨳ በ ትርጉም ፊልሞቻችን ይዝናኑ!\n\n⨳ ፊልም ልይ'ን ይጫኑ ና ደስታዎን ያስጀምሩ!"
    bot.send_photo(message.chat.id, PHOTO_URL, caption=welcome_text, reply_markup=main_markup(user_id))

# --- 📂 ADMIN: UPLOAD MOVIES (Accepts both File and Video) ---
@bot.message_handler(func=lambda m: m.text == "📂 Upload Movies" and m.from_user.id == ADMIN_ID)
def ask_for_file(message):
    msg = bot.send_message(message.chat.id, "📤 Send Me File/Video Sir (ፋይሉን ወይም ቪዲዮውን ይላኩ)")
    bot.register_next_step_handler(msg, get_media_file)

def get_media_file(message):
    file_id = None
    file_name = None
    f_type = None

    if message.content_type == 'document':
        file_id = message.document.file_id
        file_name = message.caption if message.caption else message.document.file_name
        f_type = 'document'
    elif message.content_type == 'video':
        file_id = message.video.file_id
        file_name = message.caption if message.caption else "ያልተሰየመ ቪዲዮ"
        f_type = 'video'
    else:
        bot.send_message(ADMIN_ID, "❌ እባክዎ ፋይል ወይም ቪዲዮ ብቻ ይላኩ!")
        return

    temp_data[ADMIN_ID] = {"file_id": file_id, "name": file_name, "file_type": f_type}
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⚫️ ትርጉም ሲንግል (0.5 ብር)", callback_data="set_0.5"))
    markup.add(types.InlineKeyboardButton("🟡 ትርጉም ተከታታይ (0.3 ብር)", callback_data="set_0.3"))
    markup.add(types.InlineKeyboardButton("🔵 አማርኛ (0.5 ብር)", callback_data="set_0.5"))
    markup.add(types.InlineKeyboardButton("🔴 ኢሮቲክ (1.0 ብር)", callback_data="set_1.0"))
    markup.add(types.InlineKeyboardButton("⚪️ መፅሀፍ (5.0 ብር)", callback_data="set_5.0"))
    
    bot.send_message(ADMIN_ID, f"🎬 የተቀበለው፦ {file_name}\n\nየአይነቱን ምረጥ፦", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("set_"))
def save_movie_final(call):
    price = float(call.data.split("_")[1])
    file_info = temp_data.get(ADMIN_ID)
    if file_info:
        c = conn.cursor()
        c.execute("INSERT INTO movies (name, file_id, price, file_type) VALUES (?, ?, ?, ?)", 
                  (file_info['name'], file_info['file_id'], price, file_info['file_type']))
        conn.commit()
        bot.edit_message_text(f"✅ ተሳክቷል!\n🎬 ስም: {file_info['name']}\n💰 ዋጋ: {price} ብር ተመዝግቧል።", 
                              call.message.chat.id, call.message.message_id)
        del temp_data[ADMIN_ID]

# --- 🎬 1. ፊልም ልይ! ---
@bot.message_handler(func=lambda m: m.text == "⨳ ፊልም ልይ!")
def search_start(message):
    msg = bot.send_message(message.chat.id, "⨳ የሚፈልጉትን ፊልም ስም ይፃፉ!")
    bot.register_next_step_handler(msg, process_search)

def process_search(message):
    query = message.text
    c = conn.cursor()
    c.execute("SELECT name, price FROM movies WHERE name LIKE ?", ('%' + query + '%',))
    results = c.fetchall()
    if results:
        markup = types.InlineKeyboardMarkup()
        for movie in results:
            markup.add(types.InlineKeyboardButton(text=f"📂 {movie[0]} ({movie[1]} ብር)", callback_data=f"buy_{movie[0]}"))
        bot.send_message(message.chat.id, f"ውጤቶች፦", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "⨳ በዚ ስም የተሰየመ ፊልም ማግኘት አልቻልኩም!")

# --- 💰 2. ያለኝ ሂሳብ! ---
@bot.message_handler(func=lambda m: m.text == "⨳ ያለኝ ሂሳብ!")
def check_balance(message):
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE user_id=?", (message.from_user.id,))
    res = c.fetchone()
    balance = res[0] if res else 10.0
    bot.send_message(message.chat.id, f"⨳ ቀሪ ሂሳብ ~> {balance} ብር።")

# --- 💳 3. ገቢ ላድርግ! ---
@bot.message_handler(func=lambda m: m.text == "⨳ ገቢ ላድርግ!")
def deposit_menu(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Telebirr", callback_data="pay_tele"))
    bot.send_message(message.chat.id, "⨳ ገቢ የሚያደርጉበት መንገድ በቴሌብር ብቻ ነው!", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "pay_tele")
def tele_info(call):
    msg = (
        "⨳ ምን ያህል ብር ማስገባት ይፈልጋሉ?\nክፍያ ሚፈፅሙት~> በTelebirr ነው።\n\n"
        "ትንሹ: 5 ብር | ትልቁ: 1,000 ብር።\n\n"
        "⨳ በዚህ +251961343796 የቴሌብር አካውንት ይላኩ።\n\n"
        "⨳ ልከው ከጨረሱ በኋላ Screen Shoot አንስተው ይላኩልን!"
    )
    bot.edit_message_text(msg, call.message.chat.id, call.message.message_id)

# --- 📸 SCREENSHOT & ADMIN APPROVAL ---
@bot.message_handler(content_types=['photo'])
def handle_screenshot(message):
    if message.chat.id != ADMIN_ID:
        bot.send_message(message.chat.id, "✅ Screenshot ደርሶናል! አድሚኑ እስኪያረጋግጥ ይጠብቁ።")
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ Accept", callback_data=f"approve_{message.chat.id}"),
                   types.InlineKeyboardButton("❌ Reject", callback_data=f"decline_{message.chat.id}"))
        bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)
        bot.send_message(ADMIN_ID, f"👤 ተጠቃሚ ID: {message.chat.id}\nክፍያውን ያጽድቁ፦", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_"))
def approve_deposit(call):
    uid = call.data.split("_")[1]
    msg = bot.send_message(ADMIN_ID, f"💰 ለተጠቃሚ {uid} ስንት ብር ይግባለት?")
    bot.register_next_step_handler(msg, finalize_deposit, uid)

def finalize_deposit(message, uid):
    try:
        amt = float(message.text)
        c = conn.cursor()
        c.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amt, uid))
        conn.commit()
        bot.send_message(uid, f"🎉 {amt} ብር ወደ ቀሪ ሂሳብዎ ተጨምሯል።")
        bot.send_message(ADMIN_ID, "✅ ተፈፅሟል።")
    except:
        bot.send_message(ADMIN_ID, "❌ ስህተት! ቁጥር ብቻ ያስገቡ።")

# --- 🛒 BUYING PROCESS ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def handle_buy(call):
    m_name = call.data.replace("buy_", "")
    u_id = call.from_user.id
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE user_id=?", (u_id,))
    bal = c.fetchone()[0]
    c.execute("SELECT file_id, price, file_type FROM movies WHERE name=?", (m_name,))
    m_data = c.fetchone()
    
    if m_data and bal >= m_data[1]:
        c.execute("UPDATE users SET balance = balance - ? WHERE user_id=?", (m_data[1], u_id))
        conn.commit()
        if m_data[2] == 'video':
            bot.send_video(u_id, m_data[0], caption=f"🎬 ፊልም: {m_name}")
        else:
            bot.send_document(u_id, m_data[0], caption=f"📂 ፋይል: {m_name}")
    else:
        bot.send_message(u_id, "⚠️ በቂ ሂሳብ የለዎትም።")

# --- 👥 OTHERS ---
@bot.message_handler(func=lambda m: m.text == "⨳ ጎደኛዬን ልጋብዝ!")
def invite_friends(message):
    ref_link = f"https://telegram.me/ABRSHMovies_Bot?start={message.from_user.id}"
    bot.send_message(message.chat.id, f"ጓደኞችዎን ይጋብዙ! 1 ሰው ሲጋብዙ 1 ብር ያገኛሉ፦\n{ref_link}")

@bot.message_handler(func=lambda m: m.text == "※ DM ABRSH!")
def dm_admin(message):
    bot.send_message(message.chat.id, "አድሚን👉 @ABRSHFILMBET")

@bot.message_handler(func=lambda m: m.text == "⨳ አጠቃቀም!")
def how_to(message):
    bot.send_message(message.chat.id, "🍿 የአብርሽ ፊልም ቤት ቦት አጠቃቀም መመሪያ...")

bot.polling(none_stop=True)
