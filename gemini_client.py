
import math
import random
import time

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from google.genai import errors


# =====================================
# 1. Retry Configuration
# =====================================

RETRYABLE_ERRORS = [408, 429, 500, 502, 503, 504]

MAX_RETRY_DELAY = 30  # Maximum waiting time in seconds


# =====================================
# 2. Retry-After Helper
# =====================================

def get_retry_after_seconds(error):
    """Extract Retry-After delay from the original HTTP response."""

    response = error.response

    if response is None:
        return None

    headers = getattr(response, "headers", None)

    if headers is None:
        return None

    retry_after = headers.get("Retry-After")

    if retry_after is None:
        return None

    # Retry-After can be a number of seconds.
    try:
        delay = float(retry_after)

        if math.isfinite(delay) and delay >= 0:
            return delay

    except (ValueError, TypeError):
        pass

    # Retry-After can also be an HTTP date.
    try:
        retry_date = parsedate_to_datetime(retry_after)

        if retry_date.tzinfo is None:
            retry_date = retry_date.replace(tzinfo=timezone.utc)

        current_time = datetime.now(timezone.utc)

        delay = (retry_date - current_time).total_seconds()

        if math.isfinite(delay):
            return max(0, delay)

    except (ValueError, TypeError, OverflowError):
        pass

    return None


# =====================================
# 3. Exponential Backoff with Full Jitter
# =====================================

def calculate_retry_delay(attempt):
    """Calculate retry delay using exponential backoff and full jitter."""

    base_delay = 2 ** (attempt - 1)

    capped_delay = min(base_delay, MAX_RETRY_DELAY)

    return random.uniform(0, capped_delay)


# =====================================
# 4. Gemini Response Generation
# =====================================

def generate_response(client, model, prompt, max_attempts=3):

    if (
        isinstance(max_attempts, bool)
        or not isinstance(max_attempts, int)
        or max_attempts < 1
    ):
        raise ValueError("max_attempts must be a positive integer.")

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

            if status_code not in RETRYABLE_ERRORS:
                raise

            if attempt >= max_attempts:
                raise

            retry_after = get_retry_after_seconds(error)

            if retry_after is not None:

                if retry_after > MAX_RETRY_DELAY:
                    print(
                        "\nRetry-After exceeds the maximum allowed delay. "
                        "Stopping retries."
                    )
                    raise

                wait_time = retry_after

                print(
                    f"\nServer requested Retry-After: "
                    f"{wait_time:.2f} seconds"
                )

            else:

                wait_time = calculate_retry_delay(attempt)

                print(
                    f"\nUsing Exponential Backoff with Full Jitter: "
                    f"{wait_time:.2f} seconds"
                )

            print(f"Temporary API Error: {status_code}")
            print(f"Retrying in {wait_time:.2f} seconds...")

            time.sleep(wait_time)
