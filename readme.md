
![Healthbook](https://github.com/user-attachments/assets/2c498634-3569-40f1-882e-3f12245ff138)

# Medical Assistant WhatsApp Bot

**Continuous medical follow-up across borders**

We turn a simple WhatsApp conversation into a powerful medical records. Llama-powered partner, patients naturally build their health history using photos, voice notes, and messages, while maintaining full control over their data. Our solution bridges the gap between patients and doctors, making healthcare more accessible, personal, and efficient - all through the messaging app people already use daily.

## Features

- 🤖 **Multilingual Support**: Communication in patient's preferred language
- ⚙️ **Multimodal Interactions**:
    - Medicine photo recognition
    - Lab result analysis
    - Symptom documentation
- 🏥 **Smart Medical History**: Llama-powered organization of medical information
- 🔒 **Secure Sharing**: Patient-controlled access system for healthcare providers
- 🔄 **Interactive**: Natural conversation flow

## Security & Privacy

**Data protection**

- End-to-end encryption
- GDPR compliance
- Regular security audits
- Zero-knowledge architecture

**Access Control**

- Temporary access codes for doctors
- Granular sharing controls
- Access logging
- Revocation capabilities

## Patient / Doctor - Technical Architecture

![patient_doctor](https://github.com/user-attachments/assets/6b6a8ec3-8e0c-4672-9fa5-10bf9bb1c943)

## Prerequisites

- Python 3.8+
- WhatsApp Business API access
- Groq API key
- AWS S3 bucket and credentials

## Environment Variables

Create a `.env` file with the following variables:

WHATSAPP_TOKEN=
VERIFY_TOKEN=
PHONE_NUMBER_ID=

GROQ_API_KEY=
AWS_ACCESS_KEY=
AWS_SECRET_KEY=
S3_BUCKET=

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
