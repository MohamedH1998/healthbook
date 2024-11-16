import requests
import os
from dotenv import load_dotenv

load_dotenv()

WHATSAPP_API_URL = os.getenv("WHATSAPP_API_URL")
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")

class WhatsAppAPI:
    def __init__(self):
        self.api_url = WHATSAPP_API_URL
        self.headers = {
            "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        }

    def send_message(self, phone_number: str, message: str) -> dict:
        payload = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": "text",
            "text": {"body": message},
        }
        response = requests.post(self.api_url, json=payload, headers=self.headers)
        return response.json()

    def receive_message(self, request_data: dict) -> str:
        # Extract user message from incoming WhatsApp webhook
        message = request_data["entry"][0]["changes"][0]["value"]["messages"][0]["text"]["body"]
        sender = request_data["entry"][0]["changes"][0]["value"]["messages"][0]["from"]
        return sender, message
