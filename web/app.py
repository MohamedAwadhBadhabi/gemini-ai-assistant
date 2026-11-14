
import os
import secrets
import time
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from google import genai
from google.genai import errors, types
from pydantic import BaseModel, Field

from gemini_client import generate_response


# =============================================
# 1. Application Configuration
# =============================================

BASE_DIR = Path(__file__).resolve().parent

TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

MODEL_NAME = "gemini-3.5-flash-lite"

MAX_PROMPT_LENGTH = 4000
MAX_HISTORY_MESSAGES = 20

CONVERSATION_TTL = 30 * 60  # 30 minutes in seconds

load_dotenv(BASE_DIR.parent / ".env")

API_KEY = os.getenv("GEMINI_API_KEY")

gemini_client = (
    genai.Client(
        api_key=API_KEY,
        http_options=types.HttpOptions(
            retry_options=types.HttpRetryOptions(
                attempts=1
            )
        )
    )
    if API_KEY
    else None
)


# =============================================
# 2. In-Memory Conversation Storage
# =============================================

# Each conversation stores its history and last activity time.
# Conversations expire after 30 minutes of inactivity.

conversations: dict[str, dict] = {}


def cleanup_expired_conversations():
    """Remove conversations that have exceeded their inactivity limit."""

    current_time = time.monotonic()

    expired_ids = [
        conversation_id
        for conversation_id, conversation in conversations.items()
        if current_time - conversation["last_activity"] >= CONVERSATION_TTL
    ]

    for conversation_id in expired_ids:
        del conversations[conversation_id]


# =============================================
# 3. FastAPI Application
# =============================================

app = FastAPI(
    title="Gemini AI Assistant",
    description="An AI assistant powered by Google Gemini API",
    version="1.0.0"
)


# =============================================
# 4. Static Files and Templates
# =============================================

app.mount(
    "/static",
    StaticFiles(directory=STATIC_DIR),
    name="static"
)

templates = Jinja2Templates(
    directory=TEMPLATES_DIR
)


# =============================================
# 5. Request Schemas
# =============================================

class ChatRequest(BaseModel):

    prompt: str = Field(
        min_length=1,
        max_length=MAX_PROMPT_LENGTH
    )

    conversation_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=128
    )


# =============================================
# 6. Home Endpoint
# =============================================

@app.get("/", response_class=HTMLResponse)
def home(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={}
    )


# =============================================
# 7. Chat Endpoint
# =============================================

@app.post("/chat")
def chat(request: ChatRequest):

    # Remove expired conversations before processing the request.
    cleanup_expired_conversations()

    prompt = request.prompt.strip()

    if not prompt:
        raise HTTPException(
            status_code=400,
            detail="Prompt cannot be empty."
        )

    if gemini_client is None:
        raise HTTPException(
            status_code=500,
            detail="Gemini API key is not configured."
        )

    # =========================================
    # Identify or Create Conversation
    # =========================================

    if request.conversation_id is None:

        conversation_id = secrets.token_urlsafe(32)
        conversation_history = []

        is_new_conversation = True

    else:

        conversation_id = request.conversation_id

        conversation_record = conversations.get(conversation_id)

        if conversation_record is None:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found. Please start a new chat."
            )

        conversation_history = conversation_record["history"]

        is_new_conversation = False

        # Refresh activity time when the conversation is used.
        conversation_record["last_activity"] = time.monotonic()

    # =========================================
    # Build Gemini Conversation Context
    # =========================================

    conversation = conversation_history.copy()

    conversation.append({
        "role": "user",
        "parts": [
            {"text": prompt}
        ]
    })

    # =========================================
    # Generate Gemini Response
    # =========================================

    try:

        response_text = generate_response(
            client=gemini_client,
            model=MODEL_NAME,
            prompt=conversation
        )

        # Save messages only after a successful response.
        updated_history = conversation + [
            {
                "role": "model",
                "parts": [
                    {"text": response_text}
                ]
            }
        ]

        # Keep only the latest 20 messages.
        updated_history = updated_history[-MAX_HISTORY_MESSAGES:]

        if is_new_conversation:

            conversations[conversation_id] = {
                "history": updated_history,
                "last_activity": time.monotonic()
            }

        else:

            conversations[conversation_id]["history"] = updated_history
            conversations[conversation_id]["last_activity"] = time.monotonic()

        return {
            "conversation_id": conversation_id,
            "response": response_text
        }

    except errors.APIError as error:

        http_status = 503 if error.code == 503 else 502

        raise HTTPException(
            status_code=http_status,
            detail=f"Gemini API error: {error.code}"
        ) from error

    except ValueError as error:

        raise HTTPException(
            status_code=502,
            detail=str(error)
        ) from error
