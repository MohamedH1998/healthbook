from enum import Enum
from typing import Optional, Dict
from openai import OpenAI
import requests
import logging
import os
from app.core.config import get_settings

settings = get_settings()


class WhatsAppService:
    def __init__(self):
        self.base_url = f"https://graph.facebook.com/v21.0/{settings.PHONE_NUMBER_ID}"
        self.headers = {
            "Authorization": f"Bearer {settings.WHATSAPP_API_KEY}",  # Move token to settings
            "Content-Type": "application/json",
        }
        self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)

    async def handle_audio_message(self, media_id: str, message_id: str) -> Dict:
        """Handle audio message using OpenAI's Whisper"""
        try:
            # Get audio content
            audio_content = await self.download_media(media_id)

            # Save temporarily with .ogg extension (WhatsApp audio format)
            temp_file = f"temp_{message_id}.ogg"
            with open(temp_file, "wb") as f:
                f.write(audio_content)

            # Open and transcribe with OpenAI
            with open(temp_file, "rb") as audio_file:
                transcription = self.openai_client.audio.transcriptions.create(
                    model="whisper-1", file=audio_file
                )

            # Clean up temp file
            os.remove(temp_file)

            return {"text": transcription.text, "success": True}

        except Exception as e:
            logging.error(f"Audio handling error: {e}")
            return {"error": str(e), "success": False}
        finally:
            # Ensure temp file is removed even if there's an error
            if os.path.exists(temp_file):
                os.remove(temp_file)

    async def get_media_url(self, media_id: str) -> str:
        """Get media URL from WhatsApp API"""
        try:
            # Correct URL format for media
            url = f"https://graph.facebook.com/v21.0/{media_id}"

            response = requests.get(url, headers=self.headers)
            response.raise_for_status()

            media_data = response.json()

            if "url" not in media_data:
                logging.error(f"No URL in media response: {media_data}")
                raise Exception("Media URL not found in response")

            # Get the actual media file
            media_url = media_data["url"]
            media_response = requests.get(
                media_url,
                headers={"Authorization": f"Bearer {settings.WHATSAPP_API_KEY}"},
            )
            media_response.raise_for_status()

            return media_url

        except requests.exceptions.RequestException as e:
            logging.error(f"Error getting media URL: {str(e)}")
            logging.error(
                f"Response content: {e.response.content if hasattr(e, 'response') else 'No response'}"
            )
            raise Exception(f"Failed to get media URL: {str(e)}")
        except Exception as e:
            logging.error(f"Unexpected error getting media URL: {str(e)}")
            raise Exception(f"Failed to get media URL: {str(e)}")

    async def download_media(self, media_id: str) -> bytes:
        """Download media file from WhatsApp"""
        try:
            media_url = await self.get_media_url(media_id)

            # Download the actual media file
            media_response = requests.get(
                media_url,
                headers={"Authorization": f"Bearer {settings.WHATSAPP_API_KEY}"},
            )
            media_response.raise_for_status()

            return media_response.content

        except Exception as e:
            logging.error(f"Error downloading media: {str(e)}")
            raise Exception(f"Failed to download media: {str(e)}")

    async def send_message(
        self, phone_number: str, message: str, template: Optional[Dict] = None
    ):
        url = f"{self.base_url}/messages"

        if template:
            data = {
                "messaging_product": "whatsapp",
                "to": phone_number,
                "type": "template",
                "template": template,
            }
        else:
            data = {
                "messaging_product": "whatsapp",
                "to": phone_number,
                "type": "text",
                "text": {"body": message},
            }

        try:
            response = requests.post(url, headers=self.headers, json=data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"Error sending WhatsApp message: {e}")
            return None

    async def send_document(
        self, phone_number: str, document_path: str, caption: str
    ) -> Dict:
        """Send PDF document via WhatsApp"""
        try:
            # Read file content
            with open(document_path, "rb") as file:
                file_content = file.read()

            # 1. First upload the document
            upload_url = f"{self.base_url}/media"

            # Correct upload format
            files = {
                "file": ("report.pdf", file_content, "application/pdf"),
                "messaging_product": (None, "whatsapp"),  # Add this
                "type": (None, "application/pdf"),  # Add this
            }
            headers = {
                "Authorization": f"Bearer {settings.WHATSAPP_API_KEY}"
                # Remove Content-Type header to let requests set it with boundary
            }
            # Upload file
            logging.info("Uploading document to WhatsApp servers...")
            upload_response = requests.post(upload_url, headers=headers, files=files)
            upload_response.raise_for_status()
            logging.info("Document uploaded successfully")

            # Get media ID
            media_id = upload_response.json().get("id")
            if not media_id:
                raise Exception("No media ID received from upload")

            # 2. Then send the message with the document
            message_url = f"{self.base_url}/messages"

            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": phone_number,
                "type": "document",
                "document": {
                    "id": media_id,
                    "caption": caption,
                    "filename": "medical_report.pdf",
                },
            }

            logging.info("Sending document message...")
            response = requests.post(message_url, headers=self.headers, json=payload)
            response.raise_for_status()

            logging.info(f"Document sent successfully to {phone_number}")
            return response.json()

        except FileNotFoundError:
            logging.error(f"Document not found: {document_path}")
            raise Exception(f"Document not found: {document_path}")
        except requests.exceptions.RequestException as e:
            logging.error(f"Error sending document: {str(e)}")
            if hasattr(e, "response") and e.response:
                logging.error(f"Response content: {e.response.text}")
            raise Exception(f"Failed to send document: {str(e)}")
        except Exception as e:
            logging.error(f"Unexpected error sending document: {str(e)}")
            raise
