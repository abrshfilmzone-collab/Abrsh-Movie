import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
import threading
from flask import Flask
import os

# ================= Configuration =================
TOKEN = "8673546825:AAG3tqrnD_STYgf5gtyjVdbw8awXUQD1m10"
ADMIN_ID = 7908276494

bot = telebot.TeleBot(TOKEN, parse_mode='Markdown')
app = Flask(__name__)
db_lock = threading.Lock()

temp_uploads = {}  # Store temporary movie data during admin upload

# ================= Database Setup =================
def init_db():
    with db_lock:
        with sqlite3.connect('bot.db', check_same_thread=False) as conn:
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS users
                         (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0.0)''')
            c.execute('''CREATE TABLE IF NOT EXISTS movies
                         (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, file_id TEXT, price REAL, category TEXT)''')
            conn.commit()

def execute_query(query, args=(), fetchone=False, fetchall=False, commit=False):
    with db_lock:
        with sqlite3.connect('bot.db', check_same_thread=False) as conn:
            c = conn.cursor()
            c.execute(query, args)
            res = None
            if fetchone: res = c.fetchone()
            if fetchall: res = c.fetchall()
            if commit: conn.commit()
            return res

# ================= Flask Keep-Alive =================
@app.route('/')
def index():
    return "Bot is running perfectly!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# ================= Keyboards =================
def get_main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton("※ ፊልም ልይ!"), KeyboardButton("※ ያለኝ ሂሳብ!"),
        KeyboardButton("※ ገቢ ላድርግ!"), KeyboardButton("※ ጎደኛዬን ልጋብዝ!"),
        KeyboardButton("※ አጠቃቀም!"), KeyboardButton("※ DM ABRSH!")
    )
    return markup

def get_admin_panel():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("📊 Bot Statics", callback_data="admin_stats"),
        InlineKeyboardButton("📂 Upload Movies", callback_data="admin_upload"),
        InlineKeyboardButton("⚙️ Manage Movies", callback_data="admin_manage")
    )
    return markup

# ================= Handlers =================
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    
    # Check for referral
    parts = message.text.split()
    if len(parts) > 1 and parts[1].startswith('ref'):
        try:
            referrer_id = int(parts[1][3:])
            if referrer_id != user_id:
                existing_user = execute_query("SELECT user_id FROM users WHERE user_id=?", (user_id,), fetchone=True)
                if not existing_user:
                    # Reward referrer
                    execute_query("UPDATE users SET balance = balance + 0.7 WHERE user_id=?", (referrer_id,), commit=True)
                    bot.send_message(referrer_id, "🎉 አዲስ ሰው ጋብዘዋል! 0.7 ETB ወደ ሂሳብዎ ገብቷል!")
        except ValueError:
            pass

    # Register user if not exists
    user = execute_query("SELECT user_id FROM users WHERE user_id=?", (user_id,), fetchone=True)
    if not user:
        execute_query("INSERT INTO users (user_id, balance) VALUES (?, ?)", (user_id, 0.0), commit=True)

    bot.send_message(message.chat.id, "እንኳን ደህና መጡ! ከታች ያለውን ሜኑ ይጠቀሙ።", reply_markup=get_main_menu())

    # Send admin panel to the specific admin ID
    if user_id == ADMIN_ID:
        bot.send_message(message.chat.id, "👨‍💻 **Admin Control Panel**\nWelcome back Admin!", reply_markup=get_admin_panel())


@bot.message_handler(func=lambda message: True)
def handle_menu(message):
    text = message.text
    chat_id = message.chat.id
    user_id = message.from_user.id

    if text == "※ ፊልም ልይ!":
        msg = bot.send_message(chat_id, "የሚፈልጉትን የፊልም ስም ያስገቡ:")
        bot.register_next_step_handler(msg, search_movie)

    elif text == "※ ያለኝ ሂሳብ!":
        balance = execute_query("SELECT balance FROM users WHERE user_id=?", (user_id,), fetchone=True)[0]
        bot.send_message(chat_id, f"💳 **ያለዎት ቀሪ ሂሳብ:** {balance:.2f} ETB")

    elif text == "※ ገቢ ላድርግ!":
        bot.send_message(chat_id, "ገቢ ለማድረግ እባክዎ አድሚን ያናግሩ።\n👉 @ABRSHFILMBET")

    elif text == "※ ጎደኛዬን ልጋብዝ!":
        bot_username = bot.get_me().username
        link = f"t.me/{bot_username}?start=ref{user_id}"
        bot.send_message(chat_id, f"🔗 **የእርስዎ መጋበዣ ሊንክ:**\n{link}\n\nበዚህ ሊንክ አንድ ሰው ሲጋብዙ 0.7 ETB ያገኛሉ!")

    elif text == "※ አጠቃቀም!":
        usage_text = """**🧶 የICON ከለሮች ትርጉም።**
**">">">">">">">">**
**⚫️ -> ትርጉም ተከታታይ እና ሲንግል!**
**🟢 -> ሲንግል!**
**🟡 -> ተከታታይ ትርጉም!**
**🔴 -> ሮማንስ ያለ ትርጉም!**
**🔵 -> አማርኛ!**
**🟣 -> ተከታታይ አማርኛ!**
**🟠 -> ቃና ፊልሞች!**
**⚪️ -> መፅሀፍት!**
**">">">">">">">">**
**💵 የፊልሞች ዋጋ**
**💰ሲንግል -> 0.5 ብር።**
**💰ተከታታይ -> 0.3 ብር።**
**💰አማርኛ -> 0.5 ብር።**
**💰ኢሮቲክ -> 1 ብር።**
**💰ተከታታይ አማርኛ -> 0.5 ብር።**
**💰ቃና -> 0.3 ብር።**
**💰መፅሀፍ -> 5 ብር።**
**">">">">">">">">**
**✅ @ABRSHFILMBET**"""
        bot.send_message(chat_id, usage_text)

    elif text == "※ DM ABRSH!":
        bot.send_message(chat_id, "📩 **Contact Developer / Admin:**\n👉 @ABRSHFILMBET")


# ================= Search / Next Step Handlers =================
def search_movie(message):
    search_query = message.text
    results = execute_query("SELECT id, name, price, category FROM movies WHERE name LIKE ?", ('%'+search_query+'%',), fetchall=True)
    
    if not results:
        bot.send_message(message.chat.id, "⨳ በዚ ስም የተሰየመ ፊልም ማግኘት አልቻልኩም!\n⨳ ፊደል ተሳስተው እንዳይሆን ያረጋግጡ!")
    else:
        markup = InlineKeyboardMarkup(row_width=1)
        for m_id, name, price, cat in results:
            markup.add(InlineKeyboardButton(f"{cat} {name} | {price} ETB", callback_data=f"buy_{m_id}"))
        bot.send_message(message.chat.id, "🔍 **የተገኙ ፊልሞች:**", reply_markup=markup)

def process_movie_upload(message):
    if message.chat.id != ADMIN_ID: return
    
    if message.content_type in['video', 'document']:
        file_id = message.video.file_id if message.content_type == 'video' else message.document.file_id
        name = message.caption if message.caption else "Unknown Movie"
        
        temp_uploads[message.chat.id] = {'file_id': file_id, 'name': name}
        
        markup = InlineKeyboardMarkup(row_width=2)
        cats =[
            ("⚫️ 0.5 ETB", "⚫️", 0.5), ("🟢 0.5 ETB", "🟢", 0.5),
            ("🟡 0.3 ETB", "🟡", 0.3), ("🔴 1.0 ETB", "🔴", 1.0),
            ("🔵 0.5 ETB", "🔵", 0.5), ("🟣 0.5 ETB", "🟣", 0.5),
            ("🟠 0.3 ETB", "🟠", 0.3), ("⚪️ 5.0 ETB", "⚪️", 5.0)
        ]
        
        for text, cat, price in cats:
            markup.add(InlineKeyboardButton(text, callback_data=f"cat_{cat}_{price}"))
            
        bot.send_message(message.chat.id, "Select Category & Price for the uploaded movie:", reply_markup=markup)
    else:
        msg = bot.send_message(message.chat.id, "❌ Invalid format. Please send a Video or Document.")
        bot.register_next_step_handler(msg, process_movie_upload)

# ================= Callback Query Handlers =================
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id

    # Admin: Bot Statics
    if call.data == "admin_stats":
        if user_id != ADMIN_ID: return
        total_users = execute_query("SELECT COUNT(*) FROM users", fetchone=True)[0]
        total_movies = execute_query("SELECT COUNT(*) FROM movies", fetchone=True)[0]
        bot.answer_callback_query(call.id, f"📊 Total Users: {total_users}\n🎬 Total Movies: {total_movies}", show_alert=True)

    # Admin: Upload Movies
    elif call.data == "admin_upload":
        if user_id != ADMIN_ID: return
        msg = bot.send_message(chat_id, "📂 Please send the Movie (Video/Document) along with a **Caption** (Movie Name):")
        bot.register_next_step_handler(msg, process_movie_upload)

    # Admin: Select Category for upload
    elif call.data.startswith("cat_"):
        if user_id != ADMIN_ID: return
        _, cat, price = call.data.split('_')
        
        if chat_id in temp_uploads:
            data = temp_uploads[chat_id]
            execute_query("INSERT INTO movies (name, file_id, price, category) VALUES (?, ?, ?, ?)",
                          (data['name'], data['file_id'], float(price), cat), commit=True)
            bot.edit_message_text("✅ **Movie uploaded successfully!**", chat_id, call.message.message_id)
            del temp_uploads[chat_id]

    # Admin: Manage Movies (List last 15)
    elif call.data == "admin_manage":
        if user_id != ADMIN_ID: return
        movies = execute_query("SELECT id, name FROM movies ORDER BY id DESC LIMIT 15", fetchall=True)
        if not movies:
            bot.send_message(chat_id, "No movies available.")
            return
            
        markup = InlineKeyboardMarkup(row_width=1)
        for m_id, m_name in movies:
            markup.add(InlineKeyboardButton(f"❌ {m_name}", callback_data=f"del_{m_id}"))
        bot.send_message(chat_id, "⚙️ **Manage Movies** (Click ❌ to delete):", reply_markup=markup)

    # Admin: Delete Movie
    elif call.data.startswith("del_"):
        if user_id != ADMIN_ID: return
        m_id = call.data.split('_')[1]
        execute_query("DELETE FROM movies WHERE id=?", (m_id,), commit=True)
        bot.answer_callback_query(call.id, "✅ Movie deleted successfully!", show_alert=True)
        bot.delete_message(chat_id, call.message.message_id)

    # User: Buy Movie
    elif call.data.startswith("buy_"):
        m_id = call.data.split('_')[1]
        movie = execute_query("SELECT name, file_id, price FROM movies WHERE id=?", (m_id,), fetchone=True)
        
        if movie:
            m_name, m_file_id, m_price = movie
            user_balance = execute_query("SELECT balance FROM users WHERE user_id=?", (user_id,), fetchone=True)[0]
            
            if user_balance >= m_price:
                # Deduct balance
                execute_query("UPDATE users SET balance = balance - ? WHERE user_id=?", (m_price, user_id), commit=True)
                # Send the movie file
                bot.send_document(chat_id, m_file_id, caption=f"🎬 {m_name}\n✅ በተሳካ ሁኔታ ገዝተዋል!")
                bot.answer_callback_query(call.id, "✅ Purchase Successful!")
            else:
                bot.answer_callback_query(call.id, "❌ ሂሳብዎ አነስተኛ ነው። እባክዎ ገቢ ያድርጉ!", show_alert=True)
        else:
            bot.answer_callback_query(call.id, "❌ ፊልሙ አልተገኘም!", show_alert=True)


# ================= Initialization and Execution =================
if __name__ == "__main__":
    # Initialize Database tables
    init_db()

    # Start Flask Webserver in a separate Thread (For Keep-Alive/Render)
    threading.Thread(target=run_flask).start()

    # Start Telegram Bot Polling
    print("Bot is successfully running...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
