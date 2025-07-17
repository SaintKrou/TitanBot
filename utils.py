# utils.py

import os
import logging
from telebot import TeleBot
from dotenv import load_dotenv

load_dotenv()

TMP_DIR = "tmp"
os.makedirs(TMP_DIR, exist_ok=True)

MANAGER_CHAT_ID = int(os.getenv("MANAGER_CHAT_ID"))
BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = TeleBot(BOT_TOKEN)


def save_and_send_file_from_bot(path: str, label: str):
    """
    Сохраняет и отправляет файл в чат менеджеров с подписью [label]
    """
    logging.info(f"📁 Сохраняем {path}")
    try:
        with open(path, "rb") as f:
            sent = bot.send_document(MANAGER_CHAT_ID, f, caption=f"[{label}]")
            logging.info(f"📤 Отправлен файл: {label}, file_id={sent.document.file_id}")
    except Exception as e:
        logging.error(f"❌ Ошибка при отправке файла {label}: {e}")


def find_file_id_by_label(label: str) -> str | None:
    """
    Ищет последнее сообщение с документом, у которого caption = [label]
    """
    try:
        updates = bot.get_updates(limit=100)
        messages = []
        for update in updates:
            msg = getattr(update.message, 'document', None)
            if update.message and update.message.chat.id == MANAGER_CHAT_ID and msg:
                caption = update.message.caption or ""
                if caption.strip() == f"[{label}]":
                    messages.append(update.message)

        if messages:
            latest = messages[-1]
            return latest.document.file_id
        else:
            logging.warning(f"⚠️ Файл с подписью [{label}] не найден в истории сообщений.")
            return None
    except Exception as e:
        logging.error(f"❌ Ошибка при поиске file_id по подписи [{label}]: {e}")
        return None


def restore_file_from_telegram(label: str, destination_path: str) -> bool:
    """
    Восстанавливает файл по метке (caption) из последних сообщений Telegram.
    """
    file_id = find_file_id_by_label(label)
    if not file_id:
        logging.warning(f"⚠️ file_id не найден для {label}, файл не будет загружен.")
        return False

    try:
        logging.info(f"⬇️ Получение файла {label} по file_id")
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        with open(destination_path, "wb") as f:
            f.write(downloaded_file)
        logging.info(f"✅ Восстановлен файл {label} -> {destination_path}")
        return True
    except Exception as e:
        logging.error(f"❌ Ошибка при загрузке файла {label}: {e}")
        return False