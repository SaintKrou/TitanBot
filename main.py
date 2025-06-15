import os
import logging
from telebot import TeleBot, types
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("BOT_TOKEN")
MANAGER_CHAT_ID = int(os.getenv("MANAGER_CHAT_ID"))

bot = TeleBot(TELEGRAM_TOKEN)
BOT_ID = None  # получим позже

# Состояния пользователей
user_states = {}

logging.basicConfig(level=logging.INFO)


def send_main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🔑 Вход", "💬 Чат")
    bot.send_message(chat_id, "Выберите действие:", reply_markup=markup)


@bot.message_handler(commands=['start'])
def handle_start(message):
    user_states[message.chat.id] = {"mode": None}
    send_main_menu(message.chat.id)


@bot.message_handler(func=lambda m: m.text == "🔑 Вход")
def handle_login(message):
    user_states[message.chat.id] = {"mode": "auth", "last_name": "", "awaiting_phone": False}
    bot.send_message(message.chat.id, "Введите свою фамилию:")


@bot.message_handler(func=lambda m: m.text == "💬 Чат")
def handle_chat(message):
    user_states[message.chat.id] = {"mode": "chat"}
    bot.send_message(message.chat.id, "Вы можете писать сообщение. Мы свяжем вас с менеджером.")


@bot.message_handler(func=lambda m: True, content_types=['text'], chat_types=['private'])
def handle_user_messages(message):
    state = user_states.get(message.chat.id)

    if not state:
        send_main_menu(message.chat.id)
        return

    if state["mode"] == "auth":
        if not state["last_name"]:
            state["last_name"] = message.text.strip()
            if state["last_name"].lower() == "петров":
                state["awaiting_phone"] = True
                bot.send_message(message.chat.id, "У нас несколько Петровых. Введите телефон:")
            else:
                bot.send_message(message.chat.id, f"Привет, {state['last_name']}! Вы успешно вошли.")
                user_states[message.chat.id] = {"mode": None}
                send_main_menu(message.chat.id)
        elif state.get("awaiting_phone"):
            phone = message.text.strip()
            bot.send_message(message.chat.id, f"Телефон {phone} принят. Вы вошли.")
            user_states[message.chat.id] = {"mode": None}
            send_main_menu(message.chat.id)

    elif state["mode"] == "chat":
        username = message.from_user.username or f"id{message.chat.id}"
        text = f"📩 Сообщение от @{username} (chat_id={message.chat.id}):\n{message.text}"
        sent_msg = bot.send_message(MANAGER_CHAT_ID, text)
        logging.info(f"Пересылаем сообщение менеджерам от {message.chat.id} (@{username})")


# ОБРАБОТКА СООБЩЕНИЙ В ГРУППЕ
@bot.message_handler(func=lambda m: True, content_types=['text'], chat_types=['group', 'supergroup'])
def handle_group_messages(message):
    if not message.reply_to_message:
        return

    replied = message.reply_to_message
    if replied.from_user.id != BOT_ID:
        return  # отвечено не боту

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


if __name__ == "__main__":
    logging.info("Запуск бота")
    try:
        bot_info = bot.get_me()
        BOT_ID = bot_info.id
        logging.info(f"Бот ID: {BOT_ID}")
        # Уведомление в админский чат
        bot.send_message(MANAGER_CHAT_ID, "✅ Бот активен и готов к работе.")
    except Exception as e:
        logging.error(f"Ошибка при получении информации о боте или отправке уведомления: {e}")
    bot.infinity_polling()

