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
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, file_id TEXT, price REAL)''')
    conn.commit()
    return conn

conn = init_db()
temp_data = {} # ጊዜያዊ መረጃ መያዣ

# --- 3. KEYBOARDS ---
def main_markup(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("⨳ ፊልም ልይ!", "⨳ ያለኝ ሂሳብ!")
    markup.row("⨳ ገቢ ላድርግ!", "⨳ ጎደኛዬን ልጋብዝ!")
    markup.row("⨳ አጠቃቀም!", "※ DM ABRSH!") # አንተ ባልከው መሰረት ተቀይሯል
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
            bot.send_message(referrer, "🎉 እንኳን ደስ አለዎት! በአንድ ሰው ግብዣ 1.0 ብር ተጨምሯል።")

    welcome_text = "⨳ ሰላም ይሄ የABRSH Movies Bot ነው እንኳን በደህና መጡ!\n\n⨳ በ ትርጉም ፊልሞቻችን ይዝናኑ!\n\n⨳ ፊልም ልይ'ን ይጫኑ ና ደስታዎን ያስጀምሩ!"
    bot.send_photo(message.chat.id, PHOTO_URL, caption=welcome_text, reply_markup=main_markup(user_id))

# --- 📂 ADMIN: UPLOAD MOVIES ---
@bot.message_handler(func=lambda m: m.text == "📂 Upload Movies" and m.from_user.id == ADMIN_ID)
def ask_for_file(message):
    msg = bot.send_message(message.chat.id, "📤 Send Me File Sir (ፋይሉን ብቻ ይላኩ)")
    bot.register_next_step_handler(msg, get_document_file)

def get_document_file(message):
    if message.content_type == 'document':
        file_id = message.document.file_id
        file_name = message.caption if message.caption else message.document.file_name
        temp_data[ADMIN_ID] = {"file_id": file_id, "name": file_name}
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("⚫️ ትርጉም ሲንግል (0.5 ብር)", callback_data="setprice_0.5"))
        markup.add(types.InlineKeyboardButton("🟡 ትርጉም ተከታታይ (0.3 ብር)", callback_data="setprice_0.3"))
        markup.add(types.InlineKeyboardButton("🔵 አማርኛ (0.5 ብር)", callback_data="setprice_0.5"))
        markup.add(types.InlineKeyboardButton("🔴 ኢሮቲክ (1.0 ብር)", callback_data="setprice_1.0"))
        markup.add(types.InlineKeyboardButton("⚪️ መፅሀፍ (5.0 ብር)", callback_data="setprice_5.0"))
        
        bot.send_message(ADMIN_ID, f"🎬 ፋይል: {file_name}\n\nየፋይሉን አይነት ይምረጡ፦", reply_markup=markup)
    else:
        bot.send_message(ADMIN_ID, "❌ እባክዎ ፋይል (Document) ብቻ ይላኩ!")

@bot.callback_query_handler(func=lambda call: call.data.startswith("setprice_"))
def save_movie_final(call):
    price = float(call.data.split("_")[1])
    file_info = temp_data.get(ADMIN_ID)
    if file_info:
        c = conn.cursor()
        c.execute("INSERT INTO movies (name, file_id, price) VALUES (?, ?, ?)", 
                  (file_info['name'], file_info['file_id'], price))
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
        bot.send_message(message.chat.id, f"ለ '{query}' የተገኙ ውጤቶች፦", reply_markup=markup)
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
    markup.add(types.InlineKeyboardButton("Telebirr", callback_data="pay_telebirr"))
    bot.send_message(message.chat.id, "⨳ ገቢ የሚያደርጉበት መንገድ በቴሌብር ብቻ ነው!", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "pay_telebirr")
def telebirr_info(call):
    msg = (
        "⨳ ምን ያህል ብር ማስገባት ይፈልጋሉ?\nክፍያ ሚፈፅሙት~> በTelebirr ነው።\n\n"
        "ትንሹ ማስገባት የሚችሉት መጠን:   5 ብር።\n"
        "ትልቁ ማስገባት የሚችሉት መጠን:   1,000 ብር።\n\n"
        "⨳ በዚህ +251961343796 የቴሌብር አካውንት ከ5 ብር ጀምሮ ይላኩ።\n\n"
        "⨳ ልከው ከጨረሱ በኋላ Screen Shoot አንስተው ይላኩልን!"
    )
    bot.edit_message_text(msg, call.message.chat.id, call.message.message_id)

# --- 👥 4. ጎደኛዬን ልጋብዝ! ---
@bot.message_handler(func=lambda m: m.text == "⨳ ጎደኛዬን ልጋብዝ!")
def invite(message):
    user_id = message.from_user.id
    ref_link = f"https://telegram.me/ABRSHMovies_Bot?start={user_id}"
    invite_msg = (
        "ጓደኞችዎን ይጋብዙ ና ሽልማቶች ያግኙ! 🎉\n\n"
        "የአብርሽን ፊልሞች እየኮመኮሙ እንዲደሰቱ ጓደኞችዎን ይጋብዙ!\n\n"
        "1 ሰው ሲጋብዙ > 1 ብር ያገኛሉ! \n"
        "ከታች ያለውን ልዩ የግብዣ ሊንክዎን ለጓደኞችዎ ያጋሩ ።\n"
        f"{ref_link}"
    )
    bot.send_message(message.chat.id, invite_msg)

# --- 📖 5. አጠቃቀም! ---
@bot.message_handler(func=lambda m: m.text == "⨳ አጠቃቀም!")
def usage_guide(message):
    guide = (
        "🍿 የአብርሽ ፊልም ቤት ቦት አጠቃቀም መመሪያ።\n\n"
        "⚫️ -> ትርጉም ሲንግል (0.5 ብር)\n"
        "🟡 -> ትርጉም ተከታታይ (0.3 ብር)\n"
        "🔵 -> አማርኛ (0.5 ብር)\n"
        "🔴 -> ኢሮቲክ (1 ብር)\n"
        "⚪️ -> መፅሀፍት (5 ብር)\n\n"
        "✅@ABRSHFILMBET"
    )
    bot.send_message(message.chat.id, guide)

# --- 👨‍💻 6. DM ABRSH! ---
@bot.message_handler(func=lambda m: m.text == "※ DM ABRSH!")
def dm_abrsh(message):
    bot.send_message(message.chat.id, "የዚህ ቦት አድሚን👉 @ABRSHFILMBET")

# --- 📸 SCREENSHOTS & DEPOSITS ---
@bot.message_handler(content_types=['photo'])
def handle_screenshot(message):
    if message.chat.id != ADMIN_ID:
        bot.send_message(message.chat.id, "✅ Screenshot ደርሶናል! አድሚኑ እስኪያረጋግጥ ይጠብቁ።")
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ Accept", callback_data=f"askamt_{message.chat.id}"),
                   types.InlineKeyboardButton("❌ Reject", callback_data=f"rej_{message.chat.id}"))
        bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)
        bot.send_message(ADMIN_ID, f"👤 ተጠቃሚ ID: {message.chat.id}\nክፍያውን ያጽድቁ፦", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("askamt_"))
def ask_amount(call):
    user_id = call.data.split("_")[1]
    msg = bot.send_message(ADMIN_ID, f"💰 ለተጠቃሚ {user_id} ስንት ብር ይግባለት? (ቁጥር ብቻ ይፃፉ)")
    bot.register_next_step_handler(msg, process_deposit, user_id)
    bot.answer_callback_query(call.id)

def process_deposit(message, user_id):
    try:
        amount = float(message.text)
        c = conn.cursor()
        c.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, user_id))
        conn.commit()
        bot.send_message(user_id, f"🎉 እንኳን ደስ አለዎት! {amount} ብር ወደ ቀሪ ሂሳብዎ ተጨምሯል።")
        bot.send_message(ADMIN_ID, f"✅ ተሳክቷል! {amount} ብር ገቢ ተደርጓል።")
    except:
        bot.send_message(ADMIN_ID, "❌ ስህተት! እባክዎ ቁጥር ብቻ ያስገቡ።")

@bot.callback_query_handler(func=lambda call: call.data.startswith("rej_"))
def reject_pay(call):
    user_id = call.data.split("_")[1]
    bot.send_message(user_id, "❌ ይቅርታ፣ የላኩት Screenshot ተቀባይነት አላገኘም።")
    bot.answer_callback_query(call.id, "ውድቅ ተደርጓል")

# --- 🛒 BUYING PROCESS ---
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
        bot.send_document(user_id, movie[0], caption=f"🎬 ፋይል: {movie_name}\n💰 የተቆረጠ ሂሳብ: {movie[1]} ብር")
    else:
        bot.send_message(user_id, "⚠️ በቂ ሂሳብ የለዎትም። እባክዎ ሂሳብ ይሙሉ ወይም ጓደኛ ይጋብዙ።")

bot.polling(none_stop=True)
