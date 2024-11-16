import asyncio
from datetime import datetime
from botocore.config import Config
import boto3
import logging

class Llama:
    def __init__(self, groq_client, s3_client, bucket_name):
        self.groq_client = groq_client
        self.s3_client = s3_client
        self.bucket_name = bucket_name

    async def analyze_medical_image(self, image_data: bytes) -> str:
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            key = f"temp_analysis/{timestamp}.jpg"

            # Upload image to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=image_data,
                ContentType="image/jpeg",
            )

            image_url = f"https://{self.bucket_name}.s3.eu-north-1.amazonaws.com/{key}"

            def call_groq():
                return self.groq_client.chat.completions.create(
                    model="llama-3.2-11b-vision-preview",
                    messages=[
                        {"role": "user", "content": "You're a medical assistant - analyse this image"},
                        {"role": "user", "content": {"type": "image_url", "url": image_url}},
                    ],
                    temperature=0.7,
                    max_tokens=256,
                    top_p=0.9,
                    stream=False,
                )

            loop = asyncio.get_event_loop()
            completion = await loop.run_in_executor(None, call_groq)

            return completion.choices[0].message.content

        except Exception as e:
            logging.error(f"Error analyzing image: {e}")
            return "An error occurred while analyzing the image. Please try again."
