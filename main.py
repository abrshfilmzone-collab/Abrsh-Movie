import telebot
from telebot import types
import sqlite3

# --- 1. CONFIGURATION ---
TOKEN = "8673546825:AAHMHdVQ-AKH-dQRVBLQnpvZruU5tovQDP8"
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
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, file_id TEXT, price REAL)''')
    conn.commit()
    return conn

conn = init_db()

# --- 3. KEYBOARDS ---
def main_markup(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("⨳ ፊልም ልይ!", "⨳ ያለኝ ሂሳብ!")
    markup.row("⨳ ገቢ ላድርግ!", "⨳ ጎደኛዬን ልጋብዝ!")
    markup.row("⨳ አጠቃቀም!", "⨳ DM ABRSH")
    # አድሚን ከሆንክ ብቻ የሚታይ በተን
    if user_id == ADMIN_ID:
        markup.row("📂 Upload Movies")
    return markup

# --- 4. COMMANDS ---
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
            bot.send_message(referrer, "🎉 እንኳን ደስ አለዎት! በአንድ ሰው ግبዣ 1.0 ብር ተጨምሯል።")

    welcome_text = "⨳ ሰላም ይሄ የABRSH Movies Bot ነው እንኳን በደህና መጡ!"
    bot.send_photo(message.chat.id, PHOTO_URL, caption=welcome_text, reply_markup=main_markup(user_id))

# --- 📂 ADMIN: UPLOAD MOVIES ---
@bot.message_handler(func=lambda m: m.text == "📂 Upload Movies" and m.from_user.id == ADMIN_ID)
def ask_for_file(message):
    msg = bot.send_message(message.chat.id, "📤 Send Me File Sir (ቪዲዮውን ይላኩ)")
    bot.register_next_step_handler(msg, get_video_file)

def get_video_file(message):
    if message.content_type == 'video':
        file_id = message.video.file_id
        file_name = message.caption if message.caption else "ያልተሰየመ ፊልም"
        
        markup = types.InlineKeyboardMarkup()
        # የዋጋ ተመኖች (እንደ "አጠቃቀም" ገፅህ የተሰራ)
        markup.add(types.InlineKeyboardButton("⚫️ ሲንግል (0.5 ብር)", callback_data=f"set_0.5_{file_id}_{file_name}"))
        markup.add(types.InlineKeyboardButton("🟡 ተከታታይ (0.3 ብር)", callback_data=f"set_0.3_{file_id}_{file_name}"))
        markup.add(types.InlineKeyboardButton("🔴 ኢሮቲክ (1.0 ብር)", callback_data=f"set_1.0_{file_id}_{file_name}"))
        markup.add(types.InlineKeyboardButton("⚪️ መፅሀፍ (5.0 ብር)", callback_data=f"set_5.0_{file_id}_{file_name}"))
        
        bot.send_message(ADMIN_ID, f"🎬 ፊልም: {file_name}\n\nእባክዎ የፊልሙን አይነት ይምረጡ፦", reply_markup=markup)
    else:
        bot.send_message(ADMIN_ID, "❌ እባክዎ ቪዲዮ ፋይል ብቻ ይላኩ!")

@bot.callback_query_handler(func=lambda call: call.data.startswith("set_"))
def save_movie(call):
    data = call.data.split("_")
    price = float(data[1])
    file_id = data[2]
    name = data[3]
    
    c = conn.cursor()
    c.execute("INSERT INTO movies (name, file_id, price) VALUES (?, ?, ?)", (name, file_id, price))
    conn.commit()
    
    bot.edit_message_text(f"✅ ተሳክቷል!\n🎬 ፊልም: {name}\n💰 ዋጋ: {price} ብር\n\nዳታቤዝ ላይ ተመዝግቧል።", call.message.chat.id, call.message.message_id)

# --- 🎬 ፊልም ልይ! (SEARCH) ---
@bot.message_handler(func=lambda m: m.text == "⨳ ፊልም ልይ!")
def search_start(message):
    msg = bot.send_message(message.chat.id, "⨳ የሚፈልጉትን ፊልም ስም ይፃፉ!")
    bot.register_next_step_handler(msg, process_search)

def process_search(message):
    query = message.text
    c = conn.cursor()
    c.execute("SELECT name, file_id, price FROM movies WHERE name LIKE ?", ('%' + query + '%',))
    results = c.fetchall()
    if results:
        markup = types.InlineKeyboardMarkup()
        for movie in results:
            markup.add(types.InlineKeyboardButton(text=f"🎬 {movie[0]} ({movie[2]} ብር)", callback_data=f"buy_{movie[0]}"))
        bot.send_message(message.chat.id, f"ለ '{query}' የተገኙ ውጤቶች፦", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "⨳ በዚ ስም የተሰየመ ፊልም ማግኘት አልቻልኩም!")

# --- 📸 SCREENSHOT & DEPOSIT --- (ከላይ የነበረው ኮድ ይቀጥላል...)
@bot.message_handler(content_types=['photo'])
def handle_screenshot(message):
    if message.chat.id != ADMIN_ID:
        bot.send_message(message.chat.id, "✅ Screenshot ደርሶናል! አድሚኑ እስኪያረጋግጥ ይጠብቁ።")
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ Accept", callback_data=f"ask_amount_{message.chat.id}"),
                   types.InlineKeyboardButton("❌ Reject", callback_data=f"reject_{message.chat.id}"))
        bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)
        bot.send_message(ADMIN_ID, f"👤 ተጠቃሚ ID: {message.chat.id}\nክፍያውን ያጽድቁ፦", reply_markup=markup)

# (ሌሎች የቆዩ የኮድ ክፍሎች እዚህ ጋር ይቀጥላሉ...)
@bot.message_handler(func=lambda m: m.text == "⨳ ያለኝ ሂሳብ!")
def check_balance(message):
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE user_id=?", (message.from_user.id,))
    res = c.fetchone()
    balance = res[0] if res else 10.0
    bot.send_message(message.chat.id, f"⨳ ቀሪ ሂሳብ ~> {balance} ብር።")

@bot.callback_query_handler(func=lambda call: call.data.startswith("ask_amount_"))
def ask_amount(call):
    user_id = call.data.split("_")[2]
    msg = bot.send_message(ADMIN_ID, f"💰 ለተጠቃሚ {user_id} ስንት ብር ይግባለት?")
    bot.register_next_step_handler(msg, process_deposit, user_id)

def process_deposit(message, user_id):
    amount = float(message.text)
    c = conn.cursor()
    c.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, user_id))
    conn.commit()
    bot.send_message(user_id, f"🎉 {amount} ብር ገቢ ተደርጓል።")
    bot.send_message(ADMIN_ID, "✅ ተፈፅሟል።")

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def buy_movie(call):
    movie_name = call.data.replace("buy_", "")
    user_id = call.from_user.id
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    balance = c.fetchone()[0]
    c.execute("SELECT file_id, price FROM movies WHERE name=?", (movie_name,))
    movie = c.fetchone()
    if balance >= movie[1]:
        c.execute("UPDATE users SET balance = balance - ? WHERE user_id=?", (movie[1], user_id))
        conn.commit()
        bot.send_video(user_id, movie[0], caption=f"🎬 {movie_name}")
    else:
        bot.send_message(user_id, "⚠️ በቂ ሂሳብ የለዎትም።")

bot.polling(none_stop=True)
