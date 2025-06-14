import os
import logging
import requests
from telebot import TeleBot, types
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("BOT_TOKEN")
MANAGER_CHAT_ID = int(os.getenv("MANAGER_CHAT_ID", "-1001234567890"))
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

bot = TeleBot(TELEGRAM_TOKEN)
logging.basicConfig(level=logging.INFO)

# user_states: chat_id -> dict с ключами:
# "mode" - None, "auth", "auth_phone", "chat"
# "last_name" - введённая фамилия
# "candidates" - список клиентов от API
# "client" - выбранный клиент из API (dict с полями id, имя и т.п.)
user_states = {}

def send_main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🔑 Вход", "💬 Чат")
    bot.send_message(chat_id, "Выберите действие:", reply_markup=markup)

def find_clients_by_last_name(last_name):
    try:
        resp = requests.get(f"{API_BASE_URL}/clients", params={"last_name": last_name})
        resp.raise_for_status()
        return resp.json()  # ожидаем список клиентов
    except Exception as e:
        logging.error(f"Ошибка запроса клиентов: {e}")
        return []

def find_client_by_last_name_and_phone(last_name, phone):
    try:
        resp = requests.get(f"{API_BASE_URL}/clients", params={"last_name": last_name, "phone": phone})
        resp.raise_for_status()
        clients = resp.json()
        return clients[0] if clients else None
    except Exception as e:
        logging.error(f"Ошибка запроса клиента по фамилии и телефону: {e}")
        return None

@bot.message_handler(commands=['start'])
def handle_start(message):
    logging.info(f"/start от {message.chat.id}")
    user_states[message.chat.id] = {"mode": None}
    send_main_menu(message.chat.id)

@bot.message_handler(func=lambda m: m.text == "🔑 Вход")
def handle_login_start(message):
    logging.info(f"Начало входа от {message.chat.id}")
    user_states[message.chat.id] = {"mode": "auth", "last_name": "", "candidates": [], "client": None}
    bot.send_message(message.chat.id, "Введите свою фамилию:")

@bot.message_handler(func=lambda m: m.text == "💬 Чат")
def handle_chat_mode(message):
    state = user_states.get(message.chat.id)
    if not state or not state.get("client"):
        bot.send_message(message.chat.id, "Для начала выполните вход через меню.")
        send_main_menu(message.chat.id)
        return
    logging.info(f"Вход в чат от {message.chat.id} (клиент {state['client']['id']})")
    user_states[message.chat.id]["mode"] = "chat"
    bot.send_message(message.chat.id, "Вы можете писать сообщение менеджеру.")

@bot.message_handler(func=lambda m: True)
def handle_all_messages(message):
    logging.info(f"Сообщение от {message.chat.id}: {message.text}")
    # Игнорируем сообщения из группы менеджеров в этом обработчике
    if message.chat.id == MANAGER_CHAT_ID:
        logging.info(f"Сообщение в группе менеджеров, игнорируем здесь")
        return

    state = user_states.get(message.chat.id)
    if not state:
        logging.info(f"Нет состояния для {message.chat.id}, показываем меню")
        send_main_menu(message.chat.id)
        return

    mode = state.get("mode")
    if mode == "auth":
        last_name = message.text.strip()
        state["last_name"] = last_name
        clients = find_clients_by_last_name(last_name)
        if not clients:
            bot.send_message(message.chat.id, "Клиенты с такой фамилией не найдены. Попробуйте снова.")
            return
        if len(clients) == 1:
            # Одно совпадение — сразу берем клиента
            state["client"] = clients[0]
            state["mode"] = None
            bot.send_message(message.chat.id, f"Здравствуйте, {clients[0]['first_name']}! Вход выполнен.")
            send_main_menu(message.chat.id)
        else:
            # Несколько совпадений, просим ввести телефон
            state["candidates"] = clients
            state["mode"] = "auth_phone"
            bot.send_message(message.chat.id, f"Найдено несколько клиентов с фамилией {last_name}. Введите номер телефона для уточнения:")
    elif mode == "auth_phone":
        phone = message.text.strip()
        last_name = state["last_name"]
        client = find_client_by_last_name_and_phone(last_name, phone)
        if not client:
            bot.send_message(message.chat.id, "Клиент с такой фамилией и телефоном не найден. Попробуйте снова.")
            return
        state["client"] = client
        state["mode"] = None
        bot.send_message(message.chat.id, f"Здравствуйте, {client['first_name']}! Вход выполнен.")
        send_main_menu(message.chat.id)
    elif mode == "chat":
        client = state.get("client")
        if not client:
            bot.send_message(message.chat.id, "Сначала выполните вход.")
            send_main_menu(message.chat.id)
            return
        username = message.from_user.username or str(message.chat.id)
        text_for_manager = (
            f"📩 Сообщение от @{username} (chat_id={message.chat.id}, client_id={client['id']}):\n"
            f"{message.text}"
        )
        logging.info(f"Пересылаем менеджерам: {text_for_manager}")
        bot.send_message(MANAGER_CHAT_ID, text_for_manager)
    else:
        send_main_menu(message.chat.id)

@bot.message_handler(content_types=['text'], chat_types=['supergroup', 'group'])
def handle_manager_reply(message):
    if message.chat.id != MANAGER_CHAT_ID:
        return  # Только группа менеджеров

    if not message.reply_to_message:
        logging.info("Сообщение менеджера не является ответом, игнорируем")
        return

    orig_text = message.reply_to_message.text or ""
    if "chat_id=" not in orig_text:
        logging.info("Ответ не содержит chat_id, игнорируем")
        return

    try:
        part = orig_text.split("chat_id=")[1]
        chat_id_str = part.split(",")[0].strip()
        user_chat_id = int(chat_id_str)
        logging.info(f"Отправляем ответ менеджера пользователю {user_chat_id}")
        bot.send_message(user_chat_id, f"Ответ менеджера:\n{message.text}")
    except Exception as e:
        logging.error(f"Ошибка при обработке ответа менеджера: {e}")

if __name__ == "__main__":
    logging.info("Запуск бота")
    bot.infinity_polling()
