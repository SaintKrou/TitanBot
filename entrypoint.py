import threading
import logging
import main

logging.basicConfig(level=logging.INFO)

def run_bot():
    main.run_bot()

if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
