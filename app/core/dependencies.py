from app.services.medical_assistant import MedicalAssistantService
from pinecone import Pinecone
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from app.core.config import get_settings

settings = get_settings()

# Initialize services
pc = Pinecone(api_key=settings.PINECONE_API_KEY)
index = pc.Index("medical-records")

embedding_client = OpenAIEmbeddings(
    api_key=settings.OPENAI_API_KEY, model="text-embedding-3-small", dimensions=512
)

llm = ChatOpenAI(
    api_key=settings.OPENAI_API_KEY, model="gpt-4-turbo-preview", temperature=0.7
)
