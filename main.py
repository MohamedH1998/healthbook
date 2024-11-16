import logging
from fastapi import FastAPI, Request
import requests
from typing import Optional
import os
from datetime import datetime
import boto3
from dotenv import load_dotenv
import aiohttp
from groq import Groq
import asyncio
from botocore.config import Config
from enum import Enum
from pydantic import BaseModel
from typing import List, Dict, Optional
import json
from datetime import datetime, timedelta
import geopy.distance


load_dotenv()

app = FastAPI()
logging.basicConfig(level=logging.INFO)


from fastapi import FastAPI

app = FastAPI()

WHATSAPP_TOKEN = "EAANU7HPGtJgBOxTT8Iv0jEZAKBsWMt4ZCBf9LuvZAZCuaOeGVEUamK8ZCtcuJR7JVHni4q5NKnyAUTZBOkCtZBZAlKhCMZATKiR226PXXOU1qCkZB6b6JPG31eEuSUzPR7oIOMa1UjF2DYjeLZABLpRjZCUvzRcLfaH9GlvJaG5hQmDw6dz49VRjzVdzhsBZAvDDGqYkXpdl8V8ZBZBSsHQaSruXbxhPLPt3pK2"
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")
S3_BUCKET = os.getenv("S3_BUCKET")


# Initialize S3 client with bucket verification
def initialize_s3_client():
    try:
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY,
            config=Config(signature_version="s3v4", region_name="eu-north-1"),
        )
        # Verify bucket exists
        s3_client.head_bucket(Bucket=S3_BUCKET)
        return s3_client
    except Exception as e:
        logging.error(f"S3 initialization error: {e}")
        raise Exception(f"Failed to initialize S3: {str(e)}")


try:
    s3_client = initialize_s3_client()
except Exception as e:
    logging.error(f"Failed to initialize S3 client: {e}")
    s3_client = None

# Initialize Groq client
groq_client = Groq(api_key=GROQ_API_KEY)


async def analyze_medical_image(image_data: bytes) -> str:
    """Analyze medical image using Llama-3 Vision via Groq"""
    try:
        # Upload image to S3 and get a temporary URL
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        key = f"temp_analysis/{timestamp}.jpg"

        # Upload to S3
        s3_client.put_object(
            Bucket=S3_BUCKET, Key=key, Body=image_data, ContentType="image/jpeg"
        )

        # Generate temporary URL that's publicly accessible
        image_url = f"https://{S3_BUCKET}.s3.eu-north-1.amazonaws.com/{key}"

        # Run Groq API call in a thread pool
        def call_groq():
            return groq_client.chat.completions.create(
                model="llama-3.2-11b-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "You're a medical assistant - analyse this image",
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": image_url,
                                    "detail": "low",  # Add detail level
                                },
                            },
                        ],
                    }
                ],
                temperature=0.7,
                max_tokens=256,
                top_p=0.9,
                stream=False,
            )

        # Use asyncio to run the synchronous code in a thread pool
        loop = asyncio.get_event_loop()
        completion = await loop.run_in_executor(None, call_groq)

        return completion.choices[0].message.content

    except Exception as e:
        print(f"Error analyzing image: {e}")
        return "I encountered an error analyzing the image. Please try again."


def send_message(phone_number: str, message: str, template: Optional[dict] = None):
    """Send a message using WhatsApp Cloud API"""
    url = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    print("🟣 - headers", headers)

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
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error sending message: {e}")
        return None


async def process_image_message(message: dict, phone_number: str):
    """Process incoming image messages"""
    if not s3_client:
        send_message(
            phone_number,
            "Sorry, the image processing service is currently unavailable. Please try again later.",
        )
        return

    try:
        # Download image from WhatsApp
        async with aiohttp.ClientSession() as session:
            # Get image URL
            url = f"https://graph.facebook.com/v21.0/{message['image']['id']}"
            headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}

            async with session.get(url, headers=headers) as response:
                image_data_json = await response.json()
                image_url = image_data_json.get("url")

            # Download image
            async with session.get(image_url, headers=headers) as response:
                image_data = await response.read()

        # Store image in S3 with error handling
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            key = f"health_images/{phone_number}/{timestamp}.jpg"

            s3_client.put_object(
                Bucket=S3_BUCKET, Key=key, Body=image_data, ContentType="image/jpeg"
            )
        except Exception as s3_error:
            logging.error(f"S3 upload error: {s3_error}")
            send_message(
                phone_number,
                "Sorry, there was an error saving your image. Please try again.",
            )
            return

        # Get analysis
        analysis = await analyze_medical_image(image_data)

        # Send results
        send_message(phone_number, analysis)

        # Follow-up
        send_message(
            phone_number,
            "Would you like to:\n"
            "1. Ask specific questions about the analysis\n"
            "2. Share additional symptoms\n"
            "3. See your previous analyses",
        )

    except Exception as e:
        print(f"Error processing image: {e}")
        send_message(
            phone_number,
            "I encountered an error processing your image. Please try again.",
        )


@app.get("/")
async def root():
    return {"message": "Hello World"}


async def handle_emergency_trigger(phone_number: str):
    # Implement emergency handling logic here
    logging.info(f"Emergency trigger received from {phone_number}")


@app.post("/webhook")
async def webhook(request: Request):
    # Handle incoming WhatsApp webhooks
    try:
        body = await request.json()
        if body.get("object") == "whatsapp_business_account":
            for entry in body.get("entry", []):
                for change in entry.get("changes", []):
                    if change.get("value", {}).get("messages"):
                        message = change["value"]["messages"][0]
                        phone_number = message["from"]
                        if message["type"] == "text":
                            text = message["text"]["body"]

                            # Emergency trigger keywords
                            if text.lower() in ["sos", "emergency", "help"]:
                                # Send emergency message to the user
                                await handle_emergency_trigger(phone_number)
                            # Handle canccling emergency message
                            else:
                                # Run synchronous Groq API call in a thread pool
                                def call_groq():
                                    return groq_client.chat.completions.create(
                                        model="llama-3.2-11b-vision-preview",
                                        messages=[
                                            {
                                                "role": "system",
                                                "content": "You are a helpful medical assistant.",
                                            },
                                            {"role": "user", "content": text},
                                        ],
                                        temperature=0.7,
                                        max_tokens=256,
                                        top_p=0.9,
                                        stream=False,
                                    )
                                    # Use asyncio to run the synchronous code in a thread pool

                                loop = asyncio.get_event_loop()
                                response = await loop.run_in_executor(None, call_groq)

                                # Send the message
                                send_message(
                                    phone_number, response.choices[0].message.content
                                )
                        elif message["type"] == "image":
                            logging.info("🔵 - Received image message")
                            await process_image_message(message, phone_number)
                            logging.info("🟢 - Image message processed successfully")
        return {"status": "success"}
    except Exception as e:
        logging.error(f"Error in webhook: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


@app.get("/webhook")
async def verify_webhook(request: Request):
    """Verify webhook endpoint for WhatsApp setup"""
    params = dict(request.query_params)

    if params.get("hub.mode") == "subscribe" and params.get(
        "hub.verify_token"
    ) == os.getenv("VERIFY_TOKEN"):
        return int(params.get("hub.challenge", 0))

    return {"status": "error"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
