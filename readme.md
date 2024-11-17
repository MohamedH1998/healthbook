# Medical Assistant WhatsApp Bot

A FastAPI-based WhatsApp bot that processes medical images and provides AI-powered medical assistance using Groq's LLaMA model.

## Features

- 🤖 AI-powered medical image analysis
- 💬 WhatsApp integration for easy accessibility
- 🏥 Emergency response system
- 🖼️ Image storage and management using AWS S3
- 🔄 Interactive conversation flow

## Prerequisites

- Python 3.8+
- WhatsApp Business API access
- Groq API key
- AWS S3 bucket and credentials

## Environment Variables

Create a `.env` file with the following variables:

## Local Development

1. Clone the repository:
```bash
git clone <repository-url>
cd medical-assistant-whatsapp-bot
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up your environment variables in `.env` file

5. Run the development server:
```bash
uvicorn main:app --reload
```

The server will start at `http://localhost:8000`. The `--reload` flag enables auto-reload on code changes.

Alternative way of explicit mentions of running things app
```
uvicorn api.index:app --reload --host 0.0.0.0 --port 8000
```