# entrypoint.py

import threading
import logging
import uvicorn
import api_server
import main

logging.basicConfig(level=logging.INFO)


def run_bot():
    main.run_bot()


def run_api():
    uvicorn.run(api_server.app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    run_api()
