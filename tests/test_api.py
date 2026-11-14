
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from google.genai import errors

from web import app as app_module


# =============================================
# 1. Test Fixtures
# =============================================

@pytest.fixture
def client():

    app_module.conversations.clear()

    with TestClient(app_module.app) as test_client:
        yield test_client

    app_module.conversations.clear()


# =============================================
# 2. Input Validation Tests
# =============================================

def test_chat_rejects_empty_prompt(client):

    response = client.post(
        "/chat",
        json={
            "prompt": ""
        }
    )

    assert response.status_code == 422


def test_chat_rejects_prompt_over_max_length(client):

    response = client.post(
        "/chat",
        json={
            "prompt": "A" * 4001
        }
    )

    assert response.status_code == 422


# =============================================
# 3. API Configuration Tests
# =============================================

def test_chat_returns_error_when_api_key_is_missing(
    client,
    monkeypatch
):

    monkeypatch.setattr(
        app_module,
        "gemini_client",
        None
    )

    response = client.post(
        "/chat",
        json={
            "prompt": "Hello Gemini"
        }
    )

    assert response.status_code == 500

    assert response.json() == {
        "detail": "Gemini API key is not configured."
    }


# =============================================
# 4. Successful API Tests
# =============================================

def test_chat_creates_new_conversation(
    client,
    monkeypatch
):

    def mock_generate_response(client, model, prompt):
        return "Hello! This is a mocked Gemini response."

    monkeypatch.setattr(
        app_module,
        "generate_response",
        mock_generate_response
    )

    response = client.post(
        "/chat",
        json={
            "prompt": "Hello Gemini"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["response"] == (
        "Hello! This is a mocked Gemini response."
    )

    assert data["conversation_id"]

    assert data["conversation_id"] in app_module.conversations


def test_chat_continues_existing_conversation(
    client,
    monkeypatch
):

    captured = []

    def mock_generate_response(client, model, prompt):

        captured.append(prompt)

        if len(captured) == 1:
            return "Nice to meet you, Mohamed!"

        return "Your name is Mohamed."

    monkeypatch.setattr(
        app_module,
        "generate_response",
        mock_generate_response
    )

    # First message
    first_response = client.post(
        "/chat",
        json={
            "prompt": "My name is Mohamed."
        }
    )

    assert first_response.status_code == 200

    conversation_id = first_response.json()["conversation_id"]

    # Second message using the same conversation ID
    second_response = client.post(
        "/chat",
        json={
            "prompt": "What is my name?",
            "conversation_id": conversation_id
        }
    )

    assert second_response.status_code == 200

    assert second_response.json()["conversation_id"] == conversation_id

    assert second_response.json()["response"] == (
        "Your name is Mohamed."
    )

    # Verify conversation context
    conversation = captured[1]

    assert len(conversation) == 3

    assert conversation[0]["role"] == "user"
    assert conversation[0]["parts"][0]["text"] == "My name is Mohamed."

    assert conversation[1]["role"] == "model"
    assert conversation[1]["parts"][0]["text"] == "Nice to meet you, Mohamed!"

    assert conversation[2]["role"] == "user"
    assert conversation[2]["parts"][0]["text"] == "What is my name?"


# =============================================
# 5. Conversation Security Tests
# =============================================

def test_chat_rejects_unknown_conversation_id(client):

    response = client.post(
        "/chat",
        json={
            "prompt": "Hello Gemini",
            "conversation_id": "unknown-conversation-id"
        }
    )

    assert response.status_code == 404

    assert response.json() == {
        "detail": "Conversation not found. Please start a new chat."
    }


def test_chat_does_not_accept_client_supplied_history(
    client,
    monkeypatch
):

    captured = {}

    def mock_generate_response(client, model, prompt):

        captured["conversation"] = prompt

        return "New conversation started."

    monkeypatch.setattr(
        app_module,
        "generate_response",
        mock_generate_response
    )

    response = client.post(
        "/chat",
        json={
            "prompt": "What is my name?",
            "history": [
                {
                    "role": "user",
                    "content": "My name is Mohamed."
                },
                {
                    "role": "model",
                    "content": "Your name is Mohamed."
                }
            ]
        }
    )

    assert response.status_code == 200

    conversation = captured["conversation"]

    assert len(conversation) == 1

    assert conversation[0]["role"] == "user"

    assert conversation[0]["parts"][0]["text"] == (
        "What is my name?"
    )


# =============================================
# 6. Conversation Cleanup Tests
# =============================================

def test_cleanup_removes_expired_conversations(
    client,
    monkeypatch
):

    conversation_id = "expired-conversation"

    app_module.conversations[conversation_id] = {
        "history": [],
        "last_activity": 100.0
    }

    # Simulate time passing beyond the expiration limit.
    monkeypatch.setattr(
        app_module.time,
        "monotonic",
        lambda: 100.0 + app_module.CONVERSATION_TTL + 1
    )

    app_module.cleanup_expired_conversations()

    assert conversation_id not in app_module.conversations


def test_cleanup_keeps_active_conversations(
    client,
    monkeypatch
):

    conversation_id = "active-conversation"

    app_module.conversations[conversation_id] = {
        "history": [],
        "last_activity": 100.0
    }

    # Simulate time before the expiration limit.
    monkeypatch.setattr(
        app_module.time,
        "monotonic",
        lambda: 100.0 + app_module.CONVERSATION_TTL - 1
    )

    app_module.cleanup_expired_conversations()

    assert conversation_id in app_module.conversations


def test_chat_refreshes_conversation_expiration(
    client,
    monkeypatch
):

    conversation_id = "active-conversation"

    initial_activity = 100.0

    current_time = (
        initial_activity
        + app_module.CONVERSATION_TTL
        - 1
    )

    app_module.conversations[conversation_id] = {
        "history": [
            {
                "role": "user",
                "parts": [
                    {"text": "Hello"}
                ]
            },
            {
                "role": "model",
                "parts": [
                    {"text": "Hi there!"}
                ]
            }
        ],
        "last_activity": initial_activity
    }

    # Simulate the current time just before expiration.
    monkeypatch.setattr(
        app_module.time,
        "monotonic",
        lambda: current_time
    )

    def mock_generate_response(client, model, prompt):
        return "Welcome back!"

    monkeypatch.setattr(
        app_module,
        "generate_response",
        mock_generate_response
    )

    response = client.post(
        "/chat",
        json={
            "prompt": "I am back.",
            "conversation_id": conversation_id
        }
    )

    assert response.status_code == 200

    assert response.json()["conversation_id"] == conversation_id

    updated_conversation = app_module.conversations[conversation_id]

    assert updated_conversation["last_activity"] == current_time

    assert (
        current_time - updated_conversation["last_activity"]
        < app_module.CONVERSATION_TTL
    )


# =============================================
# 7. External API Error Tests
# =============================================

def test_chat_returns_503_when_gemini_is_unavailable(
    client,
    monkeypatch
):

    def mock_generate_response(client, model, prompt):

        raise errors.APIError(
            code=503,
            response=Mock(),
            response_json={
                "error": {
                    "code": 503,
                    "message": "Service Unavailable",
                    "status": "UNAVAILABLE"
                }
            }
        )

    monkeypatch.setattr(
        app_module,
        "generate_response",
        mock_generate_response
    )

    response = client.post(
        "/chat",
        json={
            "prompt": "Hello Gemini"
        }
    )

    assert response.status_code == 503

    assert response.json() == {
        "detail": "Gemini API error: 503"
    }


def test_chat_returns_502_when_gemini_api_error(
    client,
    monkeypatch
):

    def mock_generate_response(client, model, prompt):

        raise errors.APIError(
            code=401,
            response=Mock(),
            response_json={
                "error": {
                    "code": 401,
                    "message": "Unauthorized",
                    "status": "UNAUTHENTICATED"
                }
            }
        )

    monkeypatch.setattr(
        app_module,
        "generate_response",
        mock_generate_response
    )

    response = client.post(
        "/chat",
        json={
            "prompt": "Hello Gemini"
        }
    )

    assert response.status_code == 502

    assert response.json() == {
        "detail": "Gemini API error: 401"
    }
