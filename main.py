
import os

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

from gemini_client import generate_response


# =====================================
# 1. Load Environment Variables
# =====================================

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("Error: GEMINI_API_KEY not found!")
    raise SystemExit(1)


# =====================================
# 2. Initialize Gemini Client
# =====================================

client = genai.Client(
    api_key=api_key,
    http_options=types.HttpOptions(
        retry_options=types.HttpRetryOptions(
            attempts=1
        )
    )
)

model = "gemini-3.5-flash-lite"


# =====================================
# 3. Get and Validate User Prompt
# =====================================

prompt = input("\nAsk Gemini something: ")

if not prompt.strip():
    print("Error: Prompt cannot be empty!")
    raise SystemExit(1)


# =====================================
# 4. Generate Gemini Response
# =====================================

try:

    response_text = generate_response(
        client=client,
        model=model,
        prompt=prompt.strip()
    )

    print("\n--- Gemini Response ---")
    print(response_text)


except errors.APIError as error:

    print(f"\nGemini API Error: {error.code}")

    if error.code == 400:
        print("Bad Request: Your request is invalid.")

    elif error.code == 401:
        print("Authentication Error: Check your API Key.")

    elif error.code == 403:
        print("Permission Denied: Access is not allowed.")

    elif error.code == 404:
        print("Not Found: Check the requested model.")

    elif error.code == 429:
        print("Rate Limit: API usage limit exceeded.")

    else:
        print("Please check the API configuration.")


except ValueError as error:

    print("\nResponse Error:")
    print(error)


except Exception as error:

    print("\nUnexpected Error:")
    print(error)
