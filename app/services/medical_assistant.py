from app.services.report_generator import MedicalReportGenerator
from datetime import datetime
from typing import Optional, Dict
from .whatsapp import WhatsAppService
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from pinecone import Pinecone
import uuid
import os
import logging

MEDICAL_PROMPT = """You are an AI medical assistant. Based on the user's query and the similar medical cases provided, 
generate a helpful response. Focus on identifying patterns and relevant information from similar cases.

User Query: {query}

Similar Cases:
{similar_cases}

Important Notes:
- Mention any patterns you notice across similar cases
- Highlight common symptoms, treatments, or medications if relevant
- Be clear about medical relevance and chronicity
- If the cases suggest a serious condition, recommend consulting a healthcare provider

Please provide a comprehensive response:"""


class MedicalAssistantService:
    def __init__(self, pinecone_index, embedding_client, groq_client):
        self.whatsapp = WhatsAppService()
        self.index = pinecone_index
        self.embedding_client = embedding_client
        self.groq_client = groq_client
        self.prompt_template = ChatPromptTemplate.from_template(MEDICAL_PROMPT)

    def extract_medical_context(
        self, text: str, image_url: Optional[str] = None
    ) -> dict:
        """Extract structured medical context from user text."""
        extracted_medical_context = {
            "conditions": [],
            "symptoms": [],
            "medications": [],
            "incidents": [],
            "body_parts": [],
            "image_url": None,
        }

        try:
            context_extraction = self.groq_client.chat.completions.create(
                model="llama-3.2-11b-vision-preview",
                messages=[
                    {
                        "role": "system",
                        "content": """You are a medical context analyzer. Extract and categorize medical information from the text into these categories:
                            - conditions: Any mentioned medical conditions
                            - symptoms: Reported symptoms or discomfort
                            - medications: Any medications mentioned
                            - incidents: Medical events or incidents
                            - body_parts: Mentioned body parts or areas
                            Respond only with a JSON object containing these categories.""",
                    },
                    {"role": "user", "content": text},
                ],
                temperature=0.3,
                max_tokens=256,
                top_p=0.9,
                stream=False,
                response_format={"type": "json_object"},
            )
            extracted_context = eval(context_extraction.choices[0].message.content)
            if image_url:
                extracted_context["image_url"] = image_url

            extracted_medical_context.update(extracted_context)
        except Exception as e:
            logging.error(f"Error extracting medical context: {e}")

        return extracted_medical_context

    async def process_and_respond(
        self,
        phone_number: str,
        query: str,
        chat_history=None,
        image_url: Optional[str] = None,
    ):
        try:
            # Extract medical context from the query
            medical_context = self.extract_medical_context(query, image_url)

            # Check if medical context is empty
            empty_context = {
                "conditions": [],
                "symptoms": [],
                "medications": [],
                "incidents": [],
                "body_parts": [],
                "image_url": None,
            }
            if medical_context == empty_context:
                return query

            chat_context = ""
            if chat_history:
                chat_context = "\nPrevious conversation:\n"
                for msg in chat_history:
                    chat_context += f"{msg.type}: {msg.content}\n"

            # Create embedding with context
            context_query = f"{query} {chat_context}"
            query_embedding = self.embedding_client.embed_query(context_query)

            medical_context["phone_number"] = phone_number
            vector_data = {
                "id": str(uuid.uuid4()),
                "values": query_embedding,
                "metadata": {
                    "content": query,
                    "medical_relevance": "general",
                    "condition": "",
                    "chronic": "",
                    "medications": [],
                    "body_parts": [],
                    "phone_number": phone_number,
                    "image_url": image_url or False,
                    "date": datetime.now().isoformat(),
                },
            }

            # Insert into Pinecone
            self.index.upsert(vectors=[vector_data])

            # Search Pinecone for similar cases
            results = self.index.query(
                vector=query_embedding,
                top_k=3,
                include_values=True,
                include_metadata=True,
                filter={
                    "phone_number": {
                        "$eq": phone_number
                    }  # Filter by user's phone number
                },
            )

            cases_text = self._format_cases(results.matches)

            # Include medical context in the prompt
            prompt = self.prompt_template.format_messages(
                query=query, similar_cases=cases_text, medical_context=medical_context
            )

            return {
                "success": True,
                "similar_cases": cases_text,
                "medical_context": medical_context,
                "user_id": phone_number,  # Include user identifier in response
            }
        except Exception as e:
            logging.error(f"Error in medical assistant: {e}")
            await self.whatsapp.send_message(
                phone_number=phone_number,
                message="I apologize, but I encountered an error processing your request. Please try again later.",
            )
            return {"success": False, "error": str(e)}

    def _format_cases(self, matches):
        cases_text = ""
        for i, match in enumerate(matches, 1):
            # Skip if the case doesn't belong to the user (extra safety)
            if "phone_number" not in match.metadata:
                continue

            cases_text += f"\nCase {i}:\n"
            cases_text += f"- Content: {match.metadata['content']}\n"
            cases_text += f"- Condition: {match.metadata.get('condition', 'N/A')}\n"
            cases_text += (
                f"- Medications: {', '.join(match.metadata.get('medications', []))}\n"
            )
            cases_text += (
                f"- Body Parts: {', '.join(match.metadata.get('body_parts', []))}\n"
            )
            cases_text += f"- Relevance Score: {match.score:.2f}\n"
        return cases_text

    async def collect_medical_history(self, phone_number: str) -> Dict:
        """Collect all medical history for a user"""
        try:
            history_query = "Retrieve comprehensive medical history including conditions, symptoms, medications, and incidents"
            query_embedding = self.embedding_client.embed_query(history_query)
            # Get all records for user
            results = self.index.query(
                vector=[0.0] * 512,  # Dummy vector
                top_k=100,
                # filter={"phone_number": {"$eq": phone_number}},
                include_metadata=True,
            )
            print("🟣 - results.matches", results.matches)
            medical_history = {
                "conditions": [],
                "symptoms": [],
                "medications": [],
                "incidents": [],
                "body_parts": [],
                "chronological_events": [],
            }
            for match in results.matches:
                event = {
                    "date": match.metadata.get(
                        "created_at", datetime.now().isoformat()
                    ),
                    "content": match.metadata.get("content", ""),
                    "type": match.metadata.get("medical_relevance", "general"),
                }
                medical_history["chronological_events"].append(event)

                if match.metadata.get("condition"):
                    medical_history["conditions"].append(match.metadata["condition"])
                if match.metadata.get("medications"):
                    medical_history["medications"].extend(match.metadata["medications"])
                if match.metadata.get("body_parts"):
                    medical_history["body_parts"].extend(match.metadata["body_parts"])

            return medical_history

        except Exception as e:
            logging.error(f"Error collecting medical history: {e}")
            return None

    async def generate_medical_report(self, phone_number: str) -> str:
        """Generate and send medical report"""
        try:
            # Collect medical history
            medical_history = await self.collect_medical_history(phone_number)
            print("🟢 - medical_history", medical_history)
            # return "No medical history found"
            if not medical_history:
                return "No medical history found"

            # Generate PDF
            report_generator = MedicalReportGenerator()
            pdf_path = report_generator.generate_report(medical_history, phone_number)
            print("🟢 - pdf_path", pdf_path)
            # Send via WhatsApp
            await self.whatsapp.send_document(
                phone_number=phone_number,
                document_path=pdf_path,
                caption="Here's your medical history report",
            )

            # Cleanup
            os.remove(pdf_path)

            return "Report generated and sent successfully"

        except Exception as e:
            logging.error(f"Error generating report: {e}")
            return f"Error generating report: {str(e)}"
