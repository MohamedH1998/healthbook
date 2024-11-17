from fastapi import FastAPI
from app.api.routes import webhook
import logging

app = FastAPI(title="Medical Assistant Bot")


# Include routers
app.include_router(webhook.router)


@app.get("/")
async def root():
    return {"message": "Medical Assistant Bot API"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
