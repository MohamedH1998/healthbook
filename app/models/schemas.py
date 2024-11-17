from pydantic import BaseModel
from typing import List, Optional


class WhatsAppMessage(BaseModel):
    from_: str
    type: str
    text: Optional[dict] = None
    image: Optional[dict] = None

    class Config:
        from_attributes = True


class WebhookResponse(BaseModel):
    status: str
    message: Optional[str] = None
