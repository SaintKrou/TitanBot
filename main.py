import os
import logging
import threading
import http.server
import socketserver
from telebot import TeleBot, types
from dotenv import load_dotenv
import data_store
from datetime import datetime
from utils_yadisk import download_file_yadisk

load_dotenv()

TELEGRAM_TOKEN = os.getenv("BOT_TOKEN")
MANAGER_CHAT_ID = int(os.getenv("MANAGER_CHAT_ID"))

bot = TeleBot(TELEGRAM_TOKEN)
BOT_ID = None
user_states = {}

logging.basicConfig(level=logging.INFO)

CLIENTS_LOCAL_FILE = "clients.json"
CLIENTS_REMOTE_FILE = "/titanbot/clients.json"

def send_main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    is_authorized = data_store.is_user_authorized(chat_id)
    mode = user_states.get(chat_id, {}).get("mode")

    if mode == "chat":
        markup.row("Завершить чат")
    else:
        markup.row("💬 Чат")
        if is_authorized:
            markup.row("👤 Профиль", "🚪 Выйти")
        else:
            markup.row("🔑 Вход")

    bot.send_message(chat_id, "Выберите действие:", reply_markup=markup)

@bot.message_handler(commands=['start'])
def handle_start(message):
    chat_id = message.chat.id
    if chat_id not in user_states:
        user_states[chat_id] = {"mode": None}
    send_main_menu(chat_id)

@bot.message_handler(func=lambda m: m.text == "🔑 Вход")
def handle_login(message):
    chat_id = message.chat.id
    user_states[chat_id] = {"mode": "auth", "last_name": "", "awaiting_phone": False}
    bot.send_message(chat_id, "Введите свою фамилию:")

@bot.message_handler(func=lambda m: m.text == "💬 Чат")
def handle_chat(message):
    chat_id = message.chat.id
    user_states[chat_id] = {"mode": "chat"}
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("Завершить чат")
    bot.send_message(chat_id, "✉️ Чат активен. Напишите сообщение или завершите чат:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "Завершить чат")
def handle_chat_end(message):
    chat_id = message.chat.id
    user_states[chat_id] = {"mode": None}
    bot.send_message(chat_id, "✅ Чат завершён.")
    send_main_menu(chat_id)

@bot.message_handler(func=lambda m: m.text == "🚪 Выйти")
def handle_logout(message):
    chat_id = message.chat.id
    if data_store.is_user_authorized(chat_id):
        data_store.remove_authorized_user(chat_id)
    user_states.pop(chat_id, None)
    bot.send_message(chat_id, "Вы вышли из аккаунта.")
    send_main_menu(chat_id)

@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
def handle_profile(message):
    chat_id = message.chat.id
    if not data_store.is_user_authorized(chat_id):
        bot.send_message(chat_id, "Вы не авторизованы.")
        return

    user_info = data_store.get_user_info(chat_id)
    last_name = user_info.get("last_name", "❓")
    phone = user_info.get("phone", "").strip()

    client = data_store.find_client_by_last_name_and_phone(last_name, phone)
    if not client:
        bot.send_message(chat_id, "Профиль не найден в базе клиентов.")
        return

    today = datetime.today().date()
    lines = [f"👤 *{last_name}*", f"📱 Телефон: `{phone}`"]

    if client.unlimited:
        if client.subscription_end and client.subscription_end.date() >= today:
            lines.append(f"📅 Подписка активна до {client.subscription_end.date().strftime('%d.%m.%Y')}")
            lines.append("✅ Посещения неограничены")
        else:
            lines.append("❌ Подписка истекла")
    else:
        if client.subscription_end and client.subscription_end.date() >= today:
            lines.append(f"📅 Подписка до {client.subscription_end.date().strftime('%d.%m.%Y')}")
            if client.purchased_sessions > 0:
                lines.append(f"📘 Осталось занятий: {client.purchased_sessions}")
            else:
                lines.append("⚠️ Нет оставшихся занятий")
        else:
            lines.append("❌ Подписка неактивна")
            if client.purchased_sessions > 0:
                lines.append(f"📘 Осталось {client.purchased_sessions} занятий, будут активны после продления подписки")

    bot.send_message(chat_id, "\n".join(lines), parse_mode="Markdown")

@bot.message_handler(func=lambda m: user_states.get(m.chat.id, {}).get("mode") == "auth", content_types=['text'])
def handle_auth(message):
    chat_id = message.chat.id
    state = user_states.get(chat_id)
    if not state:
        user_states[chat_id] = {"mode": None}
        send_main_menu(chat_id)
        return

    if not state["last_name"]:
        input_text = message.text.strip()
        matches = data_store.find_clients_by_exact_last_name(input_text)

        if not matches:
            bot.send_message(chat_id, "Клиент с такой фамилией не найден. Попробуйте снова или нажмите /start для отмены.")
            return

        if len(matches) == 1:
            client = matches[0]
            logging.info(f"[Авторизация] Найден один клиент: {client.last_name} {client.phone}")
            data_store.add_authorized_user(chat_id, client.last_name, client.phone or "")
            user_states[chat_id] = {"mode": None}
            bot.send_message(chat_id, f"Привет, {client.last_name}! Вы успешно вошли.")
            send_main_menu(chat_id)
            return

        state["last_name"] = input_text
        state["awaiting_phone"] = True
        bot.send_message(chat_id, "Введите номер телефона для подтверждения.\nЕсли вы не прикрепляли номер, обратитесь к поддержке.")

    elif state.get("awaiting_phone"):
        phone = message.text.strip()
        last_name = state.get("last_name", "")
        client = data_store.find_client_by_last_name_and_phone(last_name, phone)
        if client:
            logging.info(f"[Авторизация] Успешная авторизация по фамилии {last_name} и телефону {phone}")
            data_store.add_authorized_user(chat_id, client.last_name, client.phone or "")
            bot.send_message(chat_id, f"Привет, {client.last_name}! Вы успешно вошли.")
            user_states[chat_id] = {"mode": None}
            send_main_menu(chat_id)
        else:
            logging.warning(f"[Авторизация] Не найден клиент по фамилии {last_name} и телефону {phone}")
            bot.send_message(chat_id, "Не удалось найти клиента с таким номером телефона. Попробуйте снова или нажмите /start для отмены.")

@bot.message_handler(func=lambda m: user_states.get(m.chat.id, {}).get("mode") == "chat", content_types=['text'])
def handle_chat_message(message):
    chat_id = message.chat.id
    username = message.from_user.username or f"id{chat_id}"
    user_info = data_store.get_user_info(chat_id)
    is_authorized = data_store.is_user_authorized(chat_id)
    last_name = user_info.get("last_name") if is_authorized else "❌Неавторизован"

    text = (
        f"📩 Сообщение от @{username} (chat_id={chat_id}):\n"
        f"👤 Фамилия: {last_name}\n"
        f"{message.text}"
    )
    bot.send_message(MANAGER_CHAT_ID, text)
    logging.info(f"Пересылаем сообщение менеджерам от {chat_id} (@{username})")

@bot.message_handler(func=lambda m: True, content_types=['text'], chat_types=['group', 'supergroup'])
def handle_group_messages(message):
    if not message.reply_to_message:
        return

    replied = message.reply_to_message
    if replied.from_user.id != BOT_ID:
        return

    text = replied.text or ""
    if "chat_id=" not in text:
        return

    try:
        chat_id_str = text.split("chat_id=")[1].split(")")[0]
        target_chat_id = int(chat_id_str)
        bot.send_message(target_chat_id, f"Ответ менеджера:\n{message.text}")
        logging.info(f"Переслано сообщение от менеджера пользователю {target_chat_id}")
    except Exception as e:
        logging.error(f"Ошибка при парсинге chat_id: {e}")

def run_bot():
    global BOT_ID
    logging.info("Запуск бота")

    try:
        logging.info("Пробуем скачать clients.json с Яндекс.Диска...")
        success = download_file_yadisk(CLIENTS_REMOTE_FILE, CLIENTS_LOCAL_FILE)

        if success:
            logging.info("✅ Успешно скачан clients.json с Яндекс.Диска")
        else:
            logging.warning("⚠️ Не удалось скачать clients.json с Яндекс.Диска")

        logging.info("Загружаем клиентов из локального файла...")
        data_store.restore_clients_from_file()
        logging.info(f"Загружено клиентов: {len(data_store.clients)}")

        logging.info("Загружаем авторизованных пользователей...")
        data_store.restore_auth_users()
        logging.info(f"Загружено авторизованных пользователей: {len(data_store.auth_users)}")

        bot_info = bot.get_me()
        BOT_ID = bot_info.id
        logging.info(f"Бот ID: {BOT_ID}")
        bot.send_message(MANAGER_CHAT_ID, "✅ Бот активен и готов к работе.")
    except Exception as e:
        logging.error(f"❌ Ошибка при запуске бота: {e}")

    bot.infinity_polling()

def dummy_http_server():
    port = int(os.environ.get("PORT", 10000))
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        logging.info(f"Фиктивный HTTP-сервер запущен на порту {port}")
        httpd.serve_forever()

if __name__ == "__main__":
    threading.Thread(target=dummy_http_server).start()
    run_bot()
