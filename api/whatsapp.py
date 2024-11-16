import requests
import aiohttp
import logging
from typing import Optional

class WhatsAppAPI:
    def __init__(self, phone_number_id, token):
        self.phone_number_id = phone_number_id
        self.token = token
        self.url = f"https://graph.facebook.com/v21.0/{self.phone_number_id}/messages"

    def send_message(self, phone_number: str, message: str, template: Optional[dict] = None):
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

        data = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": "template" if template else "text",
            "template": template,
            "text": {"body": message} if not template else None,
        }

        try:
            response = requests.post(self.url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"Error sending message: {e}")
            return None

    async def fetch_media(self, media_id: str) -> bytes:
        media_url = f"https://graph.facebook.com/v21.0/{media_id}"
        headers = {"Authorization": f"Bearer {self.token}"}

        async with aiohttp.ClientSession() as session:
            async with session.get(media_url, headers=headers) as response:
                return await response.read()
