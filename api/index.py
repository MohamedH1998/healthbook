from fastapi import FastAPI, Request
from llama import Llama
from whatsapp import WhatsAppAPI
import os
from dotenv import load_dotenv
from botocore.config import Config
import boto3
import logging
import asyncio

load_dotenv()

app = FastAPI()

# Configuration
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")
S3_BUCKET = os.getenv("S3_BUCKET")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Initialize Clients
groq_client = Groq(api_key=GROQ_API_KEY)
s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    config=Config(signature_version="s3v4", region_name="eu-north-1"),
)

# Initialize Classes
llama = Llama(groq_client, s3_client, S3_BUCKET)
whatsapp = WhatsAppAPI(PHONE_NUMBER_ID, WHATSAPP_TOKEN)


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.post("/webhook")
async def webhook(request: Request):
    try:
        body = await request.json()
        if body.get("object") == "whatsapp_business_account":
            for entry in body.get("entry", []):
                for change in entry.get("changes", []):
                    messages = change.get("value", {}).get("messages", [])
                    if not messages:
                        continue

                    message = messages[0]
                    phone_number = message["from"]

                    if message["type"] == "text":
                        user_message = message["text"]["body"]
                        response = await llama.analyze_message(user_message)
                        whatsapp.send_message(phone_number, response)

                    elif message["type"] == "image":
                        media_id = message["image"]["id"]
                        image_data = await whatsapp.fetch_media(media_id)
                        analysis = await llama.analyze_medical_image(image_data)
                        whatsapp.send_message(phone_number, analysis)

        return {"status": "success"}
    except Exception as e:
        logging.error(f"Webhook error: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


@app.get("/webhook")
async def verify_webhook(request: Request):
    params = dict(request.query_params)
    if params.get("hub.mode") == "subscribe" and params.get("hub.verify_token") == os.getenv("VERIFY_TOKEN"):
        return int(params.get("hub.challenge", 0))
    return {"status": "error"}
