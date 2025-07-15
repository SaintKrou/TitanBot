import os
import yadisk
from dotenv import load_dotenv

load_dotenv()
y = yadisk.YaDisk(token=os.getenv("YANDEX_TOKEN"))

print("✅ Авторизация успешна" if y.check_token() else "❌ Неверный токен")
