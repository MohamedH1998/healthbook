# app/services/image_analysis.py
from datetime import datetime
import logging
from groq import Groq
import aiohttp
from app.core.config import get_settings
from app.services.storage import S3Service
import asyncio

settings = get_settings()

IMAGE_ANALYSIS_PROMPT = """You are a medical image analyzer. Analyze the image thoroughly and provide a detailed description. 
Follow this structured approach:

1. General Content:
   - What type of image is this? (Photo, document, medical scan, etc.)
   - What is the main subject/focus?
   - What is the overall quality and clarity?

2. Medical Relevance:
   If it's an injury/body part:
   - Describe the visible symptoms (swelling, discoloration, marks)
   - Location and extent
   - Any visible patterns or anomalies
   
   If it's a medication:
   - Name/type of medication
   - Form (pill, capsule, liquid, etc.)
   - Packaging details
   - Any visible instructions or warnings
   
   If it's a medical document:
   - Type of document (prescription, lab report, etc.)
   - Key information visible
   - Dates and relevant medical terms
   - Any critical values or highlights

3. Additional Details:
   - Any text visible in the image
   - Environmental context (lighting, background, etc.)
   - Any timestamps or dates
   - Quality issues that might affect interpretation

4. Clinical Observations:
   - Any notable medical significance
   - Potential concerns or points of interest
   - Quality of visual evidence

Be concise and direct. Ignore backgrounds, image quality, or non-medical details unless they affect medical interpretation.

Respond in ONE or TWO sentences highlighting ONLY the most important medical finding.

Provide your analysis in a clear, organized format."""


class ImageAnalysisService:
    def __init__(self):
        self.groq_client = Groq(api_key=settings.GROQ_API_KEY)
        self.s3_service = S3Service()

    async def download_image(self, url: str, headers: dict) -> bytes:
        """Download image from URL"""
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                return await response.read()

    async def analyze_medical_image(self, image_data: bytes, phone_number: str) -> str:
        """Analyze medical image using Llama-3 Vision via Groq"""
        try:
            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            key = f"health_images/{phone_number}/{timestamp}.jpg"

            # Upload to S3 and get URL
            image_url = await self.s3_service.upload_file(
                key=key, data=image_data, content_type="image/jpeg"
            )

            # Run Groq API call in a thread pool
            def call_groq():
                return self.groq_client.chat.completions.create(
                    model="llama-3.2-90b-vision-preview",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Analyze this medical image and extract relevant medical information. You are a third person taking clinical notes.",
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": image_url,
                                        "detail": "high",
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
            logging.error(f"Error analyzing image: {e}")
            raise Exception(f"Failed to analyze image: {str(e)}")


# Also update app/services/emergency.py which was referenced but not implemented:

# app/services/emergency.py
import logging


class EmergencyService:
    async def handle_emergency(self, phone_number: str):
        """Handle emergency situations"""
        try:
            # Implement emergency handling logic here
            # This could include:
            # - Notifying emergency contacts
            # - Sending location to emergency services
            # - Logging the emergency event
            logging.info(f"Emergency trigger received from {phone_number}")

            # Placeholder for emergency handling logic
            return {
                "status": "emergency_handled",
                "phone_number": phone_number,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logging.error(f"Error handling emergency: {e}")
            raise Exception(f"Failed to handle emergency: {str(e)}")
