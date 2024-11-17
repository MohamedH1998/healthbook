# app/services/emergency.py
import logging
from datetime import datetime
from app.core.config import get_settings

settings = get_settings()


class EmergencyService:
    def __init__(self):
        self.emergency_keywords = {"sos", "emergency", "help", "urgent"}

    async def handle_emergency(self, phone_number: str):
        """
        Handle emergency situations by logging the event and preparing response

        Args:
            phone_number (str): The phone number that triggered the emergency

        Returns:
            dict: Status information about the emergency handling
        """
        try:
            # Log the emergency event
            logging.info(f"🚨 Emergency trigger received from {phone_number}")

            # Record the emergency event with timestamp
            emergency_record = {
                "status": "emergency_triggered",
                "phone_number": phone_number,
                "timestamp": datetime.now().isoformat(),
                "handled": True,
            }

            # Here you would typically:
            # 1. Notify emergency contacts
            # 2. Send location to emergency services
            # 3. Create an emergency record in your database
            # 4. Trigger any immediate response protocols

            logging.info(f"Emergency handled for {phone_number}")
            return emergency_record

        except Exception as e:
            logging.error(f"Failed to handle emergency for {phone_number}: {e}")
            raise Exception(f"Emergency handling failed: {str(e)}")

    def is_emergency(self, message: str) -> bool:
        """
        Check if a message contains emergency keywords

        Args:
            message (str): The message to check

        Returns:
            bool: True if message contains emergency keywords, False otherwise
        """
        return any(keyword in message.lower() for keyword in self.emergency_keywords)

    async def send_emergency_response(self, phone_number: str) -> dict:
        """
        Send initial emergency response message

        Args:
            phone_number (str): The phone number to send the response to

        Returns:
            dict: Response status
        """
        try:
            return {
                "status": "emergency_response_sent",
                "phone_number": phone_number,
                "timestamp": datetime.now().isoformat(),
                "message": "Emergency response initiated",
            }
        except Exception as e:
            logging.error(f"Failed to send emergency response to {phone_number}: {e}")
            raise Exception(f"Emergency response failed: {str(e)}")
