# utils_yadisk.py

import yadisk
import logging
import os

from dotenv import load_dotenv
load_dotenv()

YANDEX_TOKEN = os.getenv("YANDEX_TOKEN")
y = yadisk.YaDisk(token=YANDEX_TOKEN)

def upload_file_yadisk(local_path: str, remote_path: str):
    try:
        # Получаем папку (например, /titanbot)
        folder = os.path.dirname(remote_path)
        if not y.exists(folder):
            y.mkdir(folder)
            logging.info(f"📁 Создана папка {folder} на Яндекс.Диске")

        y.upload(local_path, remote_path, overwrite=True)
        logging.info(f"✅ Файл {local_path} загружен в Яндекс.Диск как {remote_path}")
    except Exception as e:
        logging.error(f"❌ Ошибка при загрузке в Яндекс.Диск: {e}")


def download_file_yadisk(remote_path: str, local_path: str) -> bool:
    try:
        if y.exists(remote_path):
            y.download(remote_path, local_path)
            logging.info(f"✅ Файл {remote_path} скачан с Яндекс.Диска в {local_path}")
            return True
        else:
            logging.warning(f"⚠️ Файл {remote_path} не найден на Яндекс.Диске")
            return False
    except Exception as e:
        logging.error(f"❌ Ошибка при загрузке с Яндекс.Диска: {e}")
        return False
