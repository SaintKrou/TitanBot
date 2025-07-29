import os
import logging
from telebot import TeleBot, types
from dotenv import load_dotenv
import data_store
from datetime import datetime

load_dotenv()

TELEGRAM_TOKEN = os.getenv("BOT_TOKEN")
MANAGER_CHAT_ID = int(os.getenv("MANAGER_CHAT_ID"))

AMBIGUOUS_LAST_NAME = "петров"  # фамилия с несколькими клиентами, требующая уточнения по телефону

bot = TeleBot(TELEGRAM_TOKEN)
BOT_ID = None
user_states = {}

logging.basicConfig(level=logging.INFO)


def send_main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

    is_authorized = data_store.is_user_authorized(chat_id)
    mode = user_states.get(chat_id, {}).get("mode")

    if mode == "chat":
        markup.row("Завершить чат")
    else:
        if is_authorized:
            markup.row("💬 Чат", "👤 Профиль")
            markup.row("🚪 Выйти")
        else:
            markup.row("💬 Чат", "🔑 Вход")

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
    if not data_store.is_user_authorized(chat_id):
        bot.send_message(chat_id, "Вы не авторизованы. Пожалуйста, нажмите 🔑 Вход.")
        return
    user_states[chat_id] = {"mode": "chat"}
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("Завершить чат")
    bot.send_message(chat_id, "✉️ Чат активен. Напишите сообщение или завершите чат:", reply_markup=markup)


@bot.message_handler(func=lambda m: m.text == "Завершить чат")
def handle_chat_end(message):
    chat_id = message.chat.id
    user_states.pop(chat_id, None)
    bot.send_message(chat_id, "✅ Чат завершён.", reply_markup=types.ReplyKeyboardRemove())
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
    phone = user_info.get("phone", "")

    client = data_store.find_client_by_last_name_and_phone(last_name, phone)
    if not client:
        bot.send_message(chat_id, "Профиль не найден в базе клиентов.")
        return

    today = datetime.today().date()
    lines = [f"👤 *{last_name}*", f"📱 Телефон: `{phone}`"]

    if client.unlimited:
        if client.subscription_end and client.subscription_end.date() >= today:
            lines.append(f"🗓Подписка активна до {client.subscription_end.date().strftime('%d.%m.%Y')}")
            lines.append("✅ Посещения неограничены")
        else:
            lines.append("❌ Подписка истекла")
    else:
        if client.subscription_end and client.subscription_end.date() >= today:
            lines.append(f"🗓Подписка до {client.subscription_end.date().strftime('%d.%m.%Y')}")
            if client.purchased_sessions > 0:
                lines.append(f"📘 Осталось занятий: {client.purchased_sessions}")
            else:
                lines.append("⚠️ Нет оставшихся занятий")
        else:
            lines.append("❌ Подписка неактивна")
            if client.purchased_sessions > 0:
                lines.append(f"📘 Осталось {client.purchased_sessions} занятий, будут активны после продления подписки")

    bot.send_message(chat_id, "\n".join(lines), parse_mode="Markdown")


@bot.message_handler(func=lambda m: user_states.get(m.chat.id, {}).get("mode") in ["auth", "chat"], content_types=['text'])
def handle_user_messages(message):
    chat_id = message.chat.id
    state = user_states.get(chat_id)
    if not state:
        user_states[chat_id] = {"mode": None}
        send_main_menu(chat_id)
        return

    if state["mode"] == "auth":
        if not state["last_name"]:
            state["last_name"] = message.text.strip()
            if state["last_name"].strip().lower() == AMBIGUOUS_LAST_NAME:
                state["awaiting_phone"] = True
                bot.send_message(chat_id, "У нас несколько людей с такой фамилией. Введите ваш телефон:")
            else:
                bot.send_message(chat_id, f"Привет, {state['last_name']}! Вы успешно вошли.")
                data_store.add_authorized_user(chat_id, state["last_name"])
                user_states[chat_id] = {"mode": None}
                send_main_menu(chat_id)
        elif state.get("awaiting_phone"):
            phone = message.text.strip()
            bot.send_message(chat_id, f"Телефон {phone} принят. Вы вошли.")
            data_store.add_authorized_user(chat_id, state["last_name"], phone)
            user_states[chat_id] = {"mode": None}
            send_main_menu(chat_id)

    elif state["mode"] == "chat":
        username = message.from_user.username or f"id{chat_id}"
        user_info = data_store.get_user_info(chat_id)
        last_name = user_info.get("last_name", "❓Неизвестно")

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
        data_store.restore_clients_from_file()
        data_store.restore_auth_users()
        logging.info(f"Загружено клиентов: {len(data_store.clients)}")
        logging.info(f"Загружено авторизованных пользователей: {len(data_store.auth_users)}")

        bot_info = bot.get_me()
        BOT_ID = bot_info.id
        logging.info(f"Бот ID: {BOT_ID}")
        bot.send_message(MANAGER_CHAT_ID, "✅ Бот активен и готов к работе.")
    except Exception as e:
        logging.error(f"Ошибка при запуске бота: {e}")

    bot.infinity_polling()


if __name__ == "__main__":
    run_bot()
