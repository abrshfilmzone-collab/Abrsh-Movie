import os
import telebot
from telebot import types
import sqlite3
from flask import Flask
from threading import Thread

# --- 1. RENDER SERVER SETUP ---
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
def get_db():
    conn = sqlite3.connect('abrsh_final.db', check_same_thread=False)
    return conn

conn = get_db()
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 5.0, first_name TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS movies (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, file_id TEXT, price REAL, category TEXT)')
conn.commit()

user_states = {}

# --- 4. KEYBOARDS ---
def main_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("※ ፊልም ልይ!", "※ ያለኝ ሂሳብ!")
    markup.row("※ ገቢ ላድርግ!", "※ ጎደኛዬን ልጋብዝ!")
    markup.row("※ አጠቃቀም!", "※ DM ABRSH!")
    return markup

# --- 5. START & ADMIN PANEL ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    fname = message.from_user.first_name
    c = conn.cursor()
    if not c.execute("SELECT user_id FROM users WHERE user_id = ?", (uid,)).fetchone():
        c.execute("INSERT INTO users (user_id, balance, first_name) VALUES (?, ?, ?)", (uid, 5.0, fname))
        conn.commit()

    welcome = "**※ ሰላም ይህ የ ABRSH Movies Bot ነው እንኳን በደህና መጡ!**\n\n**※ በትረጉም ፊልሞቻችን ይዝናኑ!**\n\n**※ ፊልም ልይ'ን ይጫኑ ና ደስታዎን ያስጀምሩ!**"
    bot.send_message(message.chat.id, welcome, reply_markup=main_markup())

    if uid == ADMIN_ID:
        kb = types.InlineKeyboardMarkup(row_width=1)
        kb.add(types.InlineKeyboardButton("📊 Bot Statics", callback_data="adm_stats"),
               types.InlineKeyboardButton("📂 Upload Movies", callback_data="adm_upload"),
               types.InlineKeyboardButton("⚙️ Edit Movies", callback_data="adm_edit"))
        bot.send_message(message.chat.id, "🛠 **Admin Control Panel:**", reply_markup=kb)

# --- 6. ADMIN CALLBACKS ---
@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_"))
def admin_callbacks(call):
    if call.data == "adm_stats":
        u = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        m = conn.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
        bot.answer_callback_query(call.id, f"Users: {u} | Movies: {m}", show_alert=True)
    
    elif call.data == "adm_upload":
        msg = bot.send_message(ADMIN_ID, "📂 **ቪዲዮውን ይላኩ (Caption ላይ ስሙን ይጻፉ)...**")
        bot.register_next_step_handler(msg, process_upload)
    
    elif call.data == "adm_edit":
        movies = conn.execute("SELECT id, name FROM movies ORDER BY id DESC LIMIT 10").fetchall()
        kb = types.InlineKeyboardMarkup()
        for mid, name in movies:
            kb.add(types.InlineKeyboardButton(f"🎬 {name}", callback_data=f"editmovie_{mid}"))
        bot.send_message(ADMIN_ID, "⚙️ **ማስተካከል የሚፈልጉትን ፊልም ይምረጡ፦**", reply_markup=kb)

# --- 7. MOVIE EDIT/DELETE LOGIC ---
@bot.callback_query_handler(func=lambda c: c.data.startswith("editmovie_"))
def edit_movie_options(call):
    mid = call.data.split("_")[1]
    kb = types.InlineKeyboardMarkup()
    kb.row(types.InlineKeyboardButton("💰 ዋጋ ቀይር", callback_data=f"price_{mid}"),
           types.InlineKeyboardButton("❌ አጥፋ", callback_data=f"delete_{mid}"))
    bot.edit_message_text("ምን ማድረግ ይፈልጋሉ?", call.message.chat.id, call.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith(("price_", "delete_")))
def handle_edit_actions(call):
    action, mid = call.data.split("_")
    if action == "delete":
        conn.execute("DELETE FROM movies WHERE id=?", (mid,))
        conn.commit()
        bot.answer_callback_query(call.id, "ተሰርዟል!")
        bot.delete_message(call.message.chat.id, call.message.message_id)
    elif action == "price":
        msg = bot.send_message(ADMIN_ID, "አዲሱን ዋጋ በቁጥር ብቻ ይላኩ፦")
        bot.register_next_step_handler(msg, lambda m: update_price(m, mid))

def update_price(m, mid):
    try:
        new_p = float(m.text)
        conn.execute("UPDATE movies SET price=? WHERE id=?", (new_p, mid))
        conn.commit()
        bot.send_message(ADMIN_ID, "✅ ዋጋው ተቀይሯል!")
    except: bot.send_message(ADMIN_ID, "❌ ስህተት! ቁጥር ብቻ ያስገቡ።")

# --- 8. UPLOAD PROCESS ---
def process_upload(m):
    if not (m.video or m.document): return
    fid = m.video.file_id if m.video else m.document.file_id
    name = m.caption if m.caption else "ያልተሰየመ"
    user_states[ADMIN_ID] = {'fid': fid, 'name': name}
    kb = types.InlineKeyboardMarkup(row_width=2)
    opts = [("⚫️", 0.5), ("🟢", 0.5), ("🟡", 0.3), ("🔴", 1.0), ("🔵", 0.5), ("⚪️", 5.0)]
    for i, p in opts: kb.insert(types.InlineKeyboardButton(f"{i} {p} ብር", callback_data=f"sv_{i}_{p}"))
    bot.send_message(ADMIN_ID, f"🎬 {name}\nአይነት ይምረጡ፦", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("sv_"))
def save_movie(call):
    _, cat, prc = call.data.split("_")
    data = user_states.get(ADMIN_ID)
    if data:
        conn.execute("INSERT INTO movies (name, file_id, price, category) VALUES (?,?,?,?)", (data['name'], data['fid'], float(prc), cat))
        conn.commit()
        bot.edit_message_text(f"✅ {data['name']} ተጭኗል!", call.message.chat.id, call.message.message_id)

# --- 9. SEARCH & BUY ---
@bot.message_handler(func=lambda m: m.text == "※ ፊልም ልይ!")
def search_start(m):
    msg = bot.send_message(m.chat.id, "⨳ **የሚፈልጉትን ፊልም ስም ይፃፉ!**")
    bot.register_next_step_handler(msg, search_result)

def search_result(m):
    query = m.text
    res = conn.execute("SELECT id, name, category, price FROM movies WHERE name LIKE ?", (f'%{query}%',)).fetchall()
    if not res:
        bot.send_message(m.chat.id, "⨳ በዚ ስም የተሰየመ ፊልም ማግኘት አልቻልኩም!\n⨳ ፊደል ተሳስተው እንዳይሆን ያረጋግጡ!")
        return
    kb = types.InlineKeyboardMarkup()
    for r in res[:10]: kb.add(types.InlineKeyboardButton(f"🎬 {r[1]} {r[2]} - {r[3]} ብር", callback_data=f"buy_{r[0]}"))
    bot.send_message(m.chat.id, f"🔍 ውጤቶች ለ '{query}'", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("buy_"))
def buy_movie(call):
    mid = call.data.split("_")[1]
    mov = conn.execute("SELECT name, file_id, price FROM movies WHERE id=?", (mid,)).fetchone()
    usr = conn.execute("SELECT balance FROM users WHERE user_id=?", (call.from_user.id,)).fetchone()
    
    if usr[0] >= mov[2]:
        new_bal = usr[0] - mov[2]
        conn.execute("UPDATE users SET balance=? WHERE user_id=?", (new_bal, call.from_user.id))
        conn.commit()
        bot.send_video(call.message.chat.id, mov[1], caption=f"🎬 {mov[0]}\n💰 ቀሪ ሂሳብ፦ {new_bal} ብር")
    else:
        bot.answer_callback_query(call.id, "❌ በቂ ሂሳብ የለዎትም!", show_alert=True)

# --- 10. PAYMENT (DEPOSIT) LOGIC ---
@bot.message_handler(func=lambda m: m.text == "※ ገቢ ላድርግ!")
def deposit(m):
    bot.send_message(m.chat.id, "⨳ **ገቢ የሚያደርጉበት መንገድ ቴሌብር ነው!**\n\nበዚህ +251961343796 ስልክ ቁጥር ከ5 ብር ጀምሮ በማስገባት **Screen Shoot** ላኩ።")

@bot.message_handler(content_types=['photo'])
def handle_screenshot(m):
    kb = types.InlineKeyboardMarkup()
    kb.row(types.InlineKeyboardButton("✅ Accept", callback_data=f"pay_acc_{m.from_user.id}"),
           types.InlineKeyboardButton("❌ Reject", callback_data=f"pay_rej_{m.from_user.id}"))
    bot.forward_message(ADMIN_ID, m.chat.id, m.message_id)
    bot.send_message(ADMIN_ID, f"💰 የክፍያ ጥያቄ ከ፦ {m.from_user.first_name} (ID: {m.from_user.id})", reply_markup=kb)
    bot.send_message(m.chat.id, "⏳ ስክሪንሹቱ ተልኳል፣ አድሚኑ እስኪያረጋግጥ ይጠብቁ።")

@bot.callback_query_handler(func=lambda c: c.data.startswith("pay_"))
def payment_approval(call):
    _, action, uid = call.data.split("_")
    if action == "acc":
        msg = bot.send_message(ADMIN_ID, f"ለዚህ ተጠቃሚ (ID: {uid}) ስንት ብር ይግባለት? (ቁጥር ብቻ ጻፍ)")
        bot.register_next_step_handler(msg, lambda m: approve_pay(m, uid))
    else:
        usr = conn.execute("SELECT first_name FROM users WHERE user_id=?", (uid,)).fetchone()
        bot.send_message(uid, f"ውድ {usr[0]} ጥያቄዎ አልተሳካም❎")
        bot.send_message(ADMIN_ID, "❌ ክፍያው ውድቅ ተደርጓል።")

def approve_pay(m, uid):
    try:
        amt = float(m.text)
        curr = conn.execute("SELECT balance FROM users WHERE user_id=?", (uid,)).fetchone()[0]
        conn.execute("UPDATE users SET balance=? WHERE user_id=?", (curr + amt, uid))
        conn.commit()
        bot.send_message(uid, f"✅ ውድ ተጠቃሚ {amt} ብር በካውንትዎ ላይ ተጨምሯል!")
        bot.send_message(ADMIN_ID, f"✅ ለተጠቃሚ {uid} {amt} ብር ገቢ ሆኗል።")
    except: bot.send_message(ADMIN_ID, "❌ ስህተት! ቁጥር ብቻ ያስገቡ።")

# --- 11. USAGE & OTHER ---
@bot.message_handler(func=lambda m: m.text == "※ አጠቃቀም!")
def usage(m):
    txt = "**🧶 የICON ከለሮች ትርጉም።**\n**\">\">\">\">\">\">\">\">**\n**⚫️ -> ትርጉም ተከታታይ እና ሲንግል!**\n**🟢 -> ሲንግል!**\n**🟡 -> ተከታታይ ትርጉም!**\n**🔴 -> ሮማንስ ያለ ትርጉም!**\n**🔵 -> አማርኛ!**\n**🟣 -> ተከታታይ አማርኛ!**\n**🟠 -> ቃና ፊልሞች!**\n**⚪️ -> መፅሀፍት!**\n**\">\">\">\">\">\">\">\">**\n**💵 የፊልሞች ዋጋ**\n**💰ሲንግል -> 0.5 ብር።**\n**💰ተከታታይ -> 0.3 ብር።**\n**💰አማርኛ -> 0.5 ብር።**\n**💰ኢሮቲክ -> 1 ብር።**\n**💰ተከታታይ አማርኛ -> 0.5 ብር።**\n**💰ቃና -> 0.3 ብር።**\n**💰መፅሀፍ -> 5 ብር።**\n**\">\">\">\">\">\">\">\">**\n**✅ @ABRSHFILMBET**"
    bot.send_message(m.chat.id, txt)

@bot.message_handler(func=lambda m: m.text == "※ ያለኝ ሂሳብ!")
def bal(m):
    res = conn.execute("SELECT balance FROM users WHERE user_id=?", (m.from_user.id,)).fetchone()
    bot.send_message(m.chat.id, f"**⨳ ቀሪ ሂሳብ ~> {res[0] if res else 0.0} ብር**")

@bot.message_handler(func=lambda m: m.text == "※ DM ABRSH!")
def dm(m): bot.send_message(m.chat.id, "**የዚህ ቦት Owner👉 @ABRSHFILMBET**")

@bot.message_handler(func=lambda m: m.text == "※ ጎደኛዬን ልጋብዝ!")
def ref(m):
    link = f"https://t.me/ABRSHMovies_Bot?start=ref{m.from_user.id}"
    bot.send_message(m.chat.id, f"**ጓደኞችዎን ይጋብዙ ና ሽልማቶች ያግኙ! 🎉**\n\n1 ሰው ሲጋብዙ > 0.7 ብር ያገኛሉ!\n\n{link}")

if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.polling(none_stop=True)
