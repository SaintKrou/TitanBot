import os
import logging
import requests
from telebot import TeleBot, types
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("BOT_TOKEN")
MANAGER_CHAT_ID = os.getenv("MANAGER_CHAT_ID")
API_BASE_URL = os.getenv("API_BASE_URL")

# Проверка обязательных переменных
if not TELEGRAM_TOKEN or not MANAGER_CHAT_ID or not API_BASE_URL:
    logging.error("Недостаточно переменных окружения: BOT_TOKEN, MANAGER_CHAT_ID, API_BASE_URL")
    exit(1)

MANAGER_CHAT_ID = int(MANAGER_CHAT_ID)

bot = TeleBot(TELEGRAM_TOKEN)
logging.basicConfig(level=logging.INFO)

# Состояние: chat_id → {"mode":"auth"/"auth_phone"/"chat"/None, "last_name", "candidates", "client"}
user_states = {}

def send_main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🔑 Вход", "💬 Чат")
    bot.send_message(chat_id, "Выберите действие:", reply_markup=markup)

def find_clients_by_last_name(last_name):
    try:
        resp = requests.get(f"{API_BASE_URL}/clients/by_last_name", params={"last_name": last_name})
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logging.error(f"Ошибка запроса /clients/by_last_name: {e}")
        return []

def find_client_by_last_name_and_phone(last_name, phone):
    try:
        resp = requests.get(f"{API_BASE_URL}/clients/by_last_name", params={"last_name": last_name})
        resp.raise_for_status()
        clients = resp.json()
        for c in clients:
            if c.get("phone") == phone:
                return c
        return None
    except Exception as e:
        logging.error(f"Ошибка запроса при авторизации по телефону: {e}")
        return None

@bot.message_handler(commands=['start'])
def handle_start(m):
    logging.info(f"/start от {m.chat.id}")
    user_states[m.chat.id] = {"mode": None}
    send_main_menu(m.chat.id)

@bot.message_handler(func=lambda m: m.text == "🔑 Вход")
def handle_login_start(m):
    logging.info(f"Начало входа {m.chat.id}")
    user_states[m.chat.id] = {"mode": "auth", "last_name": "", "candidates": [], "client": None}
    bot.send_message(m.chat.id, "Введите фамилию:")

@bot.message_handler(func=lambda m: m.text == "💬 Чат")
def handle_chat_mode(m):
    st = user_states.get(m.chat.id, {})
    if not st.get("client"):
        bot.send_message(m.chat.id, "Сначала войдите через меню.")
        send_main_menu(m.chat.id)
        return
    user_states[m.chat.id]["mode"] = "chat"
    bot.send_message(m.chat.id, "Вы вошли в чат. Напишите сообщение менеджеру:")

@bot.message_handler(func=lambda m: True)
def handle_all(m):
    if m.chat.id == MANAGER_CHAT_ID:
        return

    st = user_states.get(m.chat.id)
    if not st:
        send_main_menu(m.chat.id)
        return
    mode = st["mode"]

    if mode == "auth":
        ln = m.text.strip()
        st["last_name"] = ln
        clients = find_clients_by_last_name(ln)
        if not clients:
            bot.send_message(m.chat.id, "Клиенты с такой фамилией не найдены.")
            return
        if len(clients) == 1:
            st["client"] = clients[0]
            st["mode"] = None
            bot.send_message(m.chat.id, f"Здравствуйте, {clients[0]['first_name']}! Вход успешен.")
            send_main_menu(m.chat.id)
        else:
            st["candidates"] = clients
            st["mode"] = "auth_phone"
            bot.send_message(m.chat.id, f"Несколько клиентов найдены. Введите телефон:")
    elif mode == "auth_phone":
        phone = m.text.strip()
        ln = st["last_name"]
        client = find_client_by_last_name_and_phone(ln, phone)
        if not client:
            bot.send_message(m.chat.id, "Совпадений не найдено, введите заново:")
            return
        st["client"], st["mode"] = client, None
        bot.send_message(m.chat.id, f"Здравствуйте, {client['first_name']}! Вход успешен.")
        send_main_menu(m.chat.id)
    elif mode == "chat":
        client = st.get("client")
        if not client:
            send_main_menu(m.chat.id)
            return
        username = m.from_user.username or str(m.chat.id)
        text = f"📩 Сообщение от @{username} (chat_id={m.chat.id}, client_id={client['id']}):\n{m.text}"
        bot.send_message(MANAGER_CHAT_ID, text)
    else:
        send_main_menu(m.chat.id)

@bot.message_handler(content_types=['text'], chat_types=['supergroup', 'group'])
def handle_manager_reply(m):
    if m.chat.id != MANAGER_CHAT_ID: return
    if not m.reply_to_message or "chat_id=" not in m.reply_to_message.text:
        return
    try:
        part = m.reply_to_message.text.split("chat_id=")[1]
        chat_id = int(part.split(",")[0])
        bot.send_message(chat_id, f"Ответ менеджера:\n{m.text}")
    except Exception as e:
        logging.error(f"Ошибка при пересылке ответа: {e}")

if __name__ == "__main__":
    logging.info("Запуск бота")
    bot.infinity_polling()
