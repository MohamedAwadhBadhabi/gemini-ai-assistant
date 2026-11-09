
import time

from google.genai import errors


def generate_response(client, model, prompt, max_attempts=3):

    retryable_errors = [408, 429, 500, 502, 503, 504]

    for attempt in range(1, max_attempts + 1):

        try:
            print(
                f"\nSending request... "
                f"Attempt {attempt}/{max_attempts}"
            )

            response = client.models.generate_content(
                model=model,
                contents=prompt
            )

            if not response.text:
                raise ValueError("Gemini returned an empty response.")

            return response.text

        except errors.APIError as error:

            status_code = error.code

            if status_code in retryable_errors:

                if attempt < max_attempts:

                    wait_time = 2 ** (attempt - 1)

                    print(f"\nTemporary API Error: {status_code}")
                    print(f"Retrying in {wait_time} seconds...")

                    time.sleep(wait_time)

                else:
                    raise RuntimeError(
                        "Maximum retry attempts reached. "
                        "Gemini is still unavailable."
                    ) from error

            else:
                raise
