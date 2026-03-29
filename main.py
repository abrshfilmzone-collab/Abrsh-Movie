import telebot
from telebot import types
import sqlite3

# --- 1. CONFIGURATION ---
TOKEN = "8673546825:AAEB1yHAx-qV03BvdmSF1yKNNct9_iv72x8"
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
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, file_id TEXT, price REAL DEFAULT 0.5)''')
    conn.commit()
    return conn

conn = init_db()

# --- 3. KEYBOARDS ---
def main_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("⨳ ፊልም ልይ!", "⨳ ያለኝ ሂሳብ!")
    markup.row("⨳ ገቢ ላድርግ!", "⨳ ጎደኛዬን ልጋብዝ!")
    markup.row("⨳ አጠቃቀም!", "⨳ DM ABRSH")
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
            bot.send_message(referrer, "🎉 እንኳን ደስ አለዎት! በአንድ ሰው ግብዣ 1.0 ብር ወደ አካውንትዎ ተጨምሯል።")

    welcome_text = "⨳ ሰላም ይሄ የABRSH Movies Bot ነው እንኳን በደህና መጡ!\n\n⨳ በ ትርጉም ፊልሞቻችን ይዝናኑ!\n\n⨳ ፊልም ልይ'ን ይጫኑ ና ደስታዎን ያስጀምሩ!"
    bot.send_photo(message.chat.id, PHOTO_URL, caption=welcome_text, reply_markup=main_markup())

# --- 🎬 1. ፊልም ልይ! ---
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
            markup.add(types.InlineKeyboardButton(text=f"⚫️ {movie[0]}", callback_data=f"buy_{movie[0]}"))
        bot.send_message(message.chat.id, f"Results for: {query}\nPage 1 of 1", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "⨳ በዚ ስም የተሰየመ ፊልም ማግኘት አልቻልኩም!\n⨳ ፊደል ተሳስተው እንዳይሆን ያረጋግጡ!")

# --- 💰 4. ያለኝ ሂሳብ! ---
@bot.message_handler(func=lambda m: m.text == "⨳ ያለኝ ሂሳብ!")
def check_balance(message):
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE user_id=?", (message.from_user.id,))
    res = c.fetchone()
    balance = res[0] if res else 10.0
    bot.send_message(message.chat.id, f"⨳ ቀሪ ሂሳብ ~> {balance} ብር።")

# --- 💳 2. ገቢ ላድርግ! ---
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

# --- 👥 5. ጎደኛዬን ልጋብዝ! ---
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

# --- 📖 3. አጠቃቀም! ---
@bot.message_handler(func=lambda m: m.text == "⨳ አጠቃቀም!")
def usage_guide(message):
    guide = (
        "🍿 ዋሴ ሪከርድስ ቦት ላይ እንዴት ገቢ እንደምታደርጉ የሚያሳይ ቪዲዮ ነው።\n"
        "\">\">\">\">\">\">\">\">\n"
        "🧶 የICON ከለሮች ትርጉም።\n"
        "\">\">\">\">\">\">\">\">\n"
        "⚫️ -> ትርጉም ተከታታይ እና ሲንግል!\n"
        "🟢 -> ሲንግል!\n"
        "🟡 -> ተከታታይ ትርጉም!\n"
        "🔴 -> ሮማንስ ያለ ትርጉም!\n"
        "🔵 -> አማርኛ!\n"
        "🟣 -> ተከታታይ አማርኛ!\n"
        "🟠 -> ቃና ፊልሞች!\n"
        "⚪️ -> መፅሀፍት!\n"
        "\">\">\">\">\">\">\">\">\n"
        "💵 የፊልሞች ዋጋ\n"
        "💰ሲንግል -> 0.5 ብር።\n"
        "💰ተከታታይ -> 0.3 ብር።\n"
        "💰አማርኛ -> 0.5 ብር።\n"
        "💰ኢሮቲክ -> 1 ብር።\n"
        "💰ተከታታይ አማርኛ -> 0.4 ብር።\n"
        "💰ቃና -> 0.5 ብር።\n"
        "💰መፅሀፍ -> 5 ብር。\n\n"
        "✅@ABRSHFILMBET"
    )
    bot.send_message(message.chat.id, guide)

# --- 👨‍💻 6. DM ABRSH ---
@bot.message_handler(func=lambda m: m.text == "⨳ DM ABRSH")
def dm_abrsh(message):
    bot.send_message(message.chat.id, "የዚህ ቦት አድሚን👉 @ABRSHFILMBET")

# --- ADMIN ACTIONS & SCREENSHOTS ---
@bot.message_handler(content_types=['photo'])
def handle_screenshot(message):
    if message.chat.id != ADMIN_ID:
        bot.send_message(message.chat.id, "✅ Screenshot ደርሶናል! አድሚኑ እስኪያረጋግጥ ድረስ በትዕግስት ይጠብቁ።")
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ Accept", callback_data=f"approve_{message.chat.id}"),
                   types.InlineKeyboardButton("❌ Reject", callback_data=f"reject_{message.chat.id}"))
        bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)
        bot.send_message(ADMIN_ID, f"👤 ተጠቃሚ ID: {message.chat.id}\nክፍያውን ያጽድቁ፦", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith(("approve_", "reject_")))
def admin_action(call):
    user_id = int(call.data.split("_")[1])
    if call.data.startswith("approve_"):
        bot.send_message(user_id, "🎉 የላኩት ክፍያ ተረጋግጧል! አሁን ፊልም መግዛት ይችላሉ።")
        bot.answer_callback_query(call.id, "ክፍያው ጸድቋል!")
    else:
        bot.send_message(user_id, "❌ ይቅርታ፣ የላኩት Screenshot ተቀባይነት አላገኘም።")
        bot.answer_callback_query(call.id, "ክፍያው ውድቅ ተደርጓል!")

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
        bot.send_video(user_id, movie[0], caption=f"🎬 ፊልም: {movie_name}\n💰 የተቆረጠ ሂሳብ: {movie[1]} ብር")
    else:
        bot.send_message(user_id, "⚠️ ይቅርታ፣ በቂ ሂሳብ የለዎትም። እባክዎ ሂሳብዎን ይሙሉ ወይም ጓደኛ ይጋብዙ።")

bot.polling(none_stop=True)
