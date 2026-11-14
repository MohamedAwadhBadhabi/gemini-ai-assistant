# Gemini AI Assistant

A Python-based AI assistant powered by Google's Gemini API, featuring both a command-line interface (CLI) and a web-based chat application built with FastAPI.

This project demonstrates practical AI engineering concepts, including LLM API integration, backend development, conversation management, retry strategies, error handling, and automated testing.

**GitHub Repository:** [Gemini AI Assistant](https://github.com/MohamedAwadhBadhabi/gemini-ai-assistant)

## Project Overview

Gemini AI Assistant is an application that connects to Google's Gemini API to generate AI-powered responses.

The project evolved from a simple command-line application into a web-based chat application with a dedicated backend and frontend.

The architecture separates Gemini API communication, application logic, and user interface components to improve maintainability and testability.

## Key Features

### AI Integration
- Integration with Google's Gemini API using the official `google-genai` SDK.
- Secure API key management using environment variables.
- Centralized Gemini API request handling.

### Web Chat Application
- Interactive chat interface built with HTML, CSS, and JavaScript.
- FastAPI backend for handling chat requests.
- Markdown rendering using Marked.js.
- HTML sanitization using DOMPurify.
- New Chat functionality.
- Enter to send messages and Shift + Enter for new lines.

### Conversation Management
- Server-side conversation history management.
- Unique conversation IDs generated using Python's `secrets` module.
- Independent conversation sessions.
- Client-supplied conversation history is not trusted.
- Automatic conversation expiration after 30 minutes of inactivity.
- Automatic cleanup of expired conversations.

### Retry Logic and Error Handling
- Automatic retries for selected temporary Gemini API errors.
- Support for HTTP `Retry-After` headers in seconds and HTTP-date formats.
- Exponential Backoff with Full Jitter.
- Maximum retry delay of 30 seconds.
- Maximum of three attempts by default.
- Disabled internal SDK retries to avoid overlapping retry mechanisms.
- Preservation of original Gemini API exceptions.

### Automated Testing
- API endpoint testing.
- Retry mechanism testing.
- Mocked API responses.
- Validation of success cases, failure scenarios, and edge cases.

## System Architecture

The application consists of three main layers:

**1. Frontend**
- HTML for application structure.
- CSS for styling.
- JavaScript for chat interactions and API communication.
- Marked.js for Markdown rendering.
- DOMPurify for HTML sanitization.

**2. Backend**
- FastAPI handles incoming chat requests.
- Conversation management maintains independent sessions.
- Input validation and conversation expiration.
- Error handling and API responses.

**3. Gemini Integration**
- `gemini_client.py` centralizes communication with Gemini.
- Custom retry logic handles temporary API failures.
- Environment variables protect API credentials.

### Request Flow

```text
User
  |
  v
Web Chat Interface
  |
  v
FastAPI Backend
  |
  +----> Input Validation
  |
  +----> Conversation Management
  |
  v
Gemini Client
  |
  +----> Retry Logic
  |
  v
Google Gemini API
  |
  v
Generated Response
  |
  v
FastAPI Backend
  |
  v
Web Chat Interface
```

## Technologies Used

| Category | Technologies |
|---|---|
| Programming Language | Python 3.12 |
| AI Model | gemini-3.5-flash-lite |
| AI Integration | Google Gemini API |
| Python SDK | google-genai |
| Backend | FastAPI |
| ASGI Server | Uvicorn |
| Templates | Jinja2 |
| Frontend | HTML, CSS, JavaScript |
| Markdown Rendering | Marked.js |
| HTML Sanitization | DOMPurify |
| Environment Management | python-dotenv |
| Testing | pytest, unittest.mock, httpx |
| Version Control | Git, GitHub |

## Project Structure

```text
02-Gemini-AI-Assistant/
│
├── main.py
├── gemini_client.py
├── requirements.txt
├── README.md
├── .gitignore
│
├── tests/
│   ├── test_api.py
│   └── test_retry.py
│
└── web/
    ├── app.py
    │
    ├── templates/
    │   └── index.html
    │
    └── static/
        ├── style.css
        └── script.js
```

## Installation and Setup

### 1. Clone the Repository

```bash
git clone https://github.com/MohamedAwadhBadhabi/gemini-ai-assistant.git

cd gemini-ai-assistant
```

### 2. Create a Virtual Environment

```bash
python -m venv .venv
```

### 3. Activate the Virtual Environment

**Windows:**

```bash
.venv\Scripts\activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure the Gemini API Key

Create a `.env` file in the project root directory:

```env
GEMINI_API_KEY=your_api_key_here
```

Replace `your_api_key_here` with your own Gemini API key.

**Security:** Never commit or share your `.env` file or API key.

## Running the Application

### Command-Line Interface

Run:

```bash
python main.py
```

Enter a prompt when requested to receive a response from Gemini.

### Web Application

Start the FastAPI application using Uvicorn:

```bash
uvicorn web.app:app --reload
```

Open your browser at:

```text
http://127.0.0.1:8000
```

## Retry Strategy

The application implements a custom retry mechanism to improve resilience when communicating with the Gemini API.

### Retryable HTTP Status Codes

- 408 — Request Timeout
- 429 — Too Many Requests
- 500 — Internal Server Error
- 502 — Bad Gateway
- 503 — Service Unavailable
- 504 — Gateway Timeout

### Retry Mechanism

**1. Retry-After**

Reads the server-provided retry delay, supporting both numeric seconds and HTTP-date formats.

**2. Exponential Backoff**

Increases the retry delay after consecutive failures.

**3. Full Jitter**

Randomizes the retry delay to reduce synchronized retry attempts.

**4. Maximum Delay**

Limits the retry waiting time to 30 seconds.

**5. Maximum Attempts**

Allows up to three attempts by default, including the initial request.

Non-retryable errors are raised immediately. The original API exception is preserved when retries are exhausted.

## Conversation Management

The web application maintains conversation history on the server rather than trusting history submitted by the browser.

Key implementation details:

- Each conversation receives a unique ID.
- Conversation history is isolated between sessions.
- The browser stores the conversation ID, not the authoritative conversation history.
- Conversations expire after 30 minutes of inactivity.
- Expired conversations are cleaned up during subsequent requests.
- The application retains up to 20 messages per conversation.

## API Overview

The backend exposes the following chat endpoint:

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | Serves the web chat interface |
| POST | `/chat` | Submits a prompt and receives a Gemini response |

The chat endpoint handles prompt validation, conversation management, Gemini requests, and API error responses.

## Testing

The project includes automated tests covering both API behavior and retry logic.

Run the complete test suite:

```bash
python -m pytest -v
```

### API Tests

- Empty prompt validation.
- Maximum prompt length validation.
- Missing API key handling.
- New conversation creation.
- Existing conversation continuation.
- Unknown conversation ID handling.
- Client-supplied history rejection.
- Conversation expiration and cleanup.
- Gemini API error handling.

### Retry Tests

- Successful retry.
- Maximum retry attempts.
- Non-retryable errors.
- Invalid retry configuration.
- Retry-After in seconds.
- Retry-After HTTP-date.
- Invalid Retry-After fallback.
- Maximum retry delay enforcement.

### Latest Test Results

```text
23 passed
```

The test suite uses mocked API responses and does not require live Gemini API calls.

## Security Considerations

- API credentials are loaded from environment variables.
- `.env` is excluded from version control.
- Conversation history is managed on the server.
- Client-supplied conversation history is not trusted.
- Frontend Markdown rendering uses DOMPurify for HTML sanitization.
- Virtual environments and Python cache files are excluded from Git.

## Project Scope and Limitations

This is a hands-on AI engineering portfolio project focused on integrating LLM APIs into a Python application.

It demonstrates practical implementation of API integration, backend architecture, conversation management, retry strategies, and automated testing.

The current implementation uses in-memory conversation storage. Conversation data is therefore not persistent across server restarts.

## Author

**Mohamed Awadh Ba Dhabi**

[GitHub](https://github.com/MohamedAwadhBadhabi)