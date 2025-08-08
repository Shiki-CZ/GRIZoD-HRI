import requests
from config import LOG_URL, SERVER_ENABLED

class DataLogger:
    def __init__(self, log_url=LOG_URL):
        self.log_url = log_url

    def log(self, message):
        if SERVER_ENABLED:
            print(message)
            try:
                requests.post(self.log_url, json={"log": message})
            except Exception as e:
                print(f"Failed to send log to server: {e}")