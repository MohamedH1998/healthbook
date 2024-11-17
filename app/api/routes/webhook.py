# app/api/routes/webhook.py
from fastapi import APIRouter, Request, HTTPException, Depends
from app.services.whatsapp import WhatsAppService
from app.services.image_analysis import ImageAnalysisService
from app.services.emergency import EmergencyService
from app.services.medical_assistant import MedicalAssistantService
from app.models.schemas import WebhookResponse
from app.core.config import get_settings
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from groq import Groq
from pinecone import Pinecone  # Add this import
import os
import asyncio
import logging
from langchain.memory import ConversationBufferMemory
from langchain.memory.chat_message_histories import RedisChatMessageHistory
import redis
from typing import Dict

router = APIRouter()
settings = get_settings()
groq_client = Groq(api_key=settings.GROQ_API_KEY)
# Initialize Pinecone
pinecone_client = Pinecone(api_key=settings.PINECONE_API_KEY)
pinecone_index = pinecone_client.Index("medical-records")
OPENAI_API_KEY = settings.OPENAI_API_KEY
EMBEDDINGS_DIMENSIONS = 512

# Initialize embedding service
# Initialize OpenAI embeddings
embedding_client = OpenAIEmbeddings(
    api_key=OPENAI_API_KEY,
    model="text-embedding-3-small",
    dimensions=EMBEDDINGS_DIMENSIONS,
)

# Initialize services
whatsapp_service = WhatsAppService()
image_service = ImageAnalysisService()
emergency_service = EmergencyService()
medical_assistant = MedicalAssistantService(
    pinecone_index=pinecone_index,
    embedding_client=embedding_client,
    groq_client=groq_client,
)

# Initialize Redis client
redis_client = redis.Redis(host="localhost", port=6379, db=0)


class ConversationManager:
    def __init__(self):
        self.memories: Dict[str, ConversationBufferMemory] = {}

    def get_memory(self, phone_number: str) -> ConversationBufferMemory:
        """Get or create memory for a user"""
        if phone_number not in self.memories:
            message_history = RedisChatMessageHistory(
                url="redis://localhost:6379/0", session_id=f"chat:{phone_number}"
            )

            self.memories[phone_number] = ConversationBufferMemory(
                memory_key="chat_history",
                chat_memory=message_history,
                return_messages=True,
            )

        return self.memories[phone_number]


# Initialize conversation manager
conversation_manager = ConversationManager()


async def handle_text_message(message: dict, phone_number: str):
    """Handle incoming text messages"""
    try:
        text = message["text"]["body"].lower()

        # Get memory for this user
        memory = conversation_manager.get_memory(phone_number)

        memory = conversation_manager.get_memory(phone_number)

        # Add clear chat history functionality
        if text == "clear chat history":
            try:
                redis_client.flushall()
                await whatsapp_service.send_message(
                    phone_number=phone_number,
                    message="Chat history has been cleared successfully.",
                )
                return
            except Exception as e:
                logging.error(f"Error clearing cache: {e}")
                await whatsapp_service.send_message(
                    phone_number=phone_number,
                    message="Sorry, there was an error clearing the chat history.",
                )
                return

        if any(keyword in text for keyword in ["report", "history", "summary"]):
            result = await medical_assistant.generate_medical_report(phone_number)

            if "Error" in result:
                await whatsapp_service.send_message(
                    phone_number=phone_number,
                    message="Sorry, I couldn't generate your report. Please try again later.",
                )
            else:
                await whatsapp_service.send_message(
                    phone_number=phone_number,
                    message="I've prepared your medical history report and am sending it now.",
                )

        elif text in ["sos", "emergency", "help"]:
            await emergency_service.handle_emergency(phone_number)
            await whatsapp_service.send_message(
                phone_number,
                "Emergency services have been notified. Stay calm and wait for assistance.",
            )
        else:
            # Save user message to memory
            memory.save_context(
                {"input": text}, {"output": "Processing your message..."}
            )

            # Get chat history
            chat_history = memory.chat_memory.messages[-5:]  # Last 5 messages

            # Process with context
            processed_text = await medical_assistant.process_and_respond(
                phone_number=phone_number, query=text, chat_history=chat_history
            )

            def call_groq():
                return groq_client.chat.completions.create(
                    model="llama-3.2-11b-vision-preview",
                    messages=[
                        {
                            "role": "system",
                            "content": "You're Matthew, a helpful AI medical assistant, you are given a medical context and a patient query, you need to respond to the user query based on the medical context. Speak to the patient as an AI assistant who has been texted by the patient. Be concise and to the point & considerate you only have 70 tokens to respond - you must be concise",
                        },
                        {
                            "role": "user",
                            "content": f"Chat History: {chat_history}\n\nCurrent Context: {processed_text}",
                        },
                    ],
                    temperature=0.7,
                    max_tokens=70,
                    top_p=0.9,
                    stream=False,
                )

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, call_groq)
            response_text = response.choices[0].message.content

            # Save assistant response to memory
            memory.save_context({"input": text}, {"output": response_text})

            await whatsapp_service.send_message(phone_number, response_text)

    except Exception as e:
        logging.error(f"Error handling text message: {e}")
        raise


async def handle_image_message(message: dict, phone_number: str):
    """Handle incoming image messages"""
    try:
        # Get image URL from WhatsApp
        image_url = await whatsapp_service.get_media_url(message["image"]["id"])

        # Download image
        headers = {
            "Authorization": f"Bearer {settings.WHATSAPP_API_KEY}",
            "Content-Type": "application/json",
        }
        image_data = await image_service.download_image(image_url, headers)

        # Analyze image
        analysis = await image_service.analyze_medical_image(image_data, phone_number)
        processed_text = await medical_assistant.process_and_respond(
            phone_number=phone_number, query=analysis, image_url=image_url
        )

        # Send results
        def call_groq():
            return groq_client.chat.completions.create(
                model="llama-3.2-11b-vision-preview",
                messages=[
                    {
                        "role": "system",
                        "content": "You're Matthew, a helpful AI medical assistant, you are given a medical context and a patient query, you need to respond to the user query based on the medical context. Speak to the patient as an AI assistant who has been texted by the patient. Be concise and to the point & considerate you only have 70 tokens to respond - you must be concise",
                    },
                    {"role": "user", "content": f"""{processed_text}"""},
                ],
                temperature=0.7,
                max_tokens=100,
                top_p=0.9,
                stream=False,
            )

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, call_groq)
        await whatsapp_service.send_message(
            phone_number, response.choices[0].message.content
        )

    except Exception as e:
        logging.error(f"Error processing image: {e}")
        await whatsapp_service.send_message(
            phone_number,
            "I encountered an error processing your image. Please try again.",
        )


async def handle_audio_message(message: dict, phone_number: str):
    """Handle audio messages"""
    try:
        media_id = message["audio"]["id"]
        message_id = message["id"]

        # Process audio and get transcription
        transcription_result = await whatsapp_service.handle_audio_message(
            media_id=media_id, message_id=message_id
        )

        if "error" in transcription_result:
            await whatsapp_service.send_message(
                phone_number=phone_number,
                message="Sorry, I couldn't process that audio message. Could you try again?",
            )
            return

        # Process transcribed text through medical assistant
        processed_text = await medical_assistant.process_and_respond(
            phone_number=phone_number, query=transcription_result["text"]
        )

        # Send response back to user - modified to handle string response
        # Send results
        def call_groq():
            return groq_client.chat.completions.create(
                model="llama-3.2-11b-vision-preview",
                messages=[
                    {
                        "role": "system",
                        "content": "You're Matthew, a helpful AI medical assistant, you are given a medical context and a patient query, you need to respond to the user query based on the medical context. Speak to the patient as an AI assistant who has been texted by the patient. Be concise and to the point & considerate you only have 70 tokens to respond - you must be concise",
                    },
                    {"role": "user", "content": f"""{processed_text}"""},
                ],
                temperature=0.7,
                max_tokens=100,
                top_p=0.9,
                stream=False,
            )

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, call_groq)
        await whatsapp_service.send_message(
            phone_number, response.choices[0].message.content
        )

    except Exception as e:
        logging.error(f"Error processing audio message: {e}")
        await whatsapp_service.send_message(
            phone_number=phone_number,
            message="Sorry, there was an error processing your audio message.",
        )


@router.post("/webhook", response_model=WebhookResponse)
async def webhook(request: Request):
    """Handle incoming WhatsApp webhooks"""
    try:
        body = await request.json()

        if body.get("object") != "whatsapp_business_account":
            raise HTTPException(status_code=400, detail="Invalid webhook object")

        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                # Check if this is a message notification
                if change.get("value", {}).get("messaging_product") != "whatsapp":
                    continue

                messages = change.get("value", {}).get("messages", [])

                # Skip if no messages or if it's a status update
                if not messages or "status" in change.get("value", {}):
                    continue

                message = messages[0]
                # Ensure this is a user-initiated message
                if not message.get("from") or message.get(
                    "context"
                ):  # Skip replies/system messages
                    continue

                phone_number = message["from"]

                if message["type"] == "text":
                    await handle_text_message(message, phone_number)
                elif message["type"] == "image":
                    await handle_image_message(message, phone_number)
                elif message["type"] == "audio":
                    await handle_audio_message(message, phone_number)

        return WebhookResponse(status="success")
    except Exception as e:
        logging.error(f"Webhook error: {e}", exc_info=True)
        return WebhookResponse(status="error", message=str(e))


@router.get("/webhook")
async def verify_webhook(request: Request):
    """Verify webhook endpoint for WhatsApp setup"""
    params = dict(request.query_params)

    if (
        params.get("hub.mode") == "subscribe"
        and params.get("hub.verify_token") == settings.VERIFY_TOKEN
    ):
        return int(params.get("hub.challenge", 0))

    raise HTTPException(status_code=400, detail="Invalid verification token")
