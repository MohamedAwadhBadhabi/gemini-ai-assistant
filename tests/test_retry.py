
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from unittest.mock import Mock, patch, call

import pytest
from google.genai import errors

from gemini_client import (
    generate_response,
    get_retry_after_seconds
)


# =====================================
# Helper: Create API Error
# =====================================

def create_api_error(status_code, retry_after=None):

    response = Mock()

    response.headers = {}

    if retry_after is not None:
        response.headers["Retry-After"] = retry_after

    return errors.APIError(
        status_code,
        {"error": {"message": "Test API Error"}},
        response=response
    )


# =====================================
# TEST 1: Retry succeeds
# =====================================

def test_retry_success():

    fake_client = Mock()

    successful_response = Mock()
    successful_response.text = "Gemini request succeeded!"

    fake_client.models.generate_content.side_effect = [
        errors.APIError(
            503,
            {"error": {"message": "Service Unavailable"}}
        ),
        successful_response
    ]

    with patch("gemini_client.time.sleep") as mocked_sleep, \
         patch("gemini_client.random.uniform", return_value=0.75) as mocked_random:

        result = generate_response(
            client=fake_client,
            model="fake-model",
            prompt="Test prompt"
        )

    assert result == "Gemini request succeeded!"
    assert fake_client.models.generate_content.call_count == 2

    mocked_random.assert_called_once_with(0, 1)
    assert mocked_sleep.call_args_list == [call(0.75)]

    print("\nTEST 1 PASSED: Retry succeeded.")


# =====================================
# TEST 2: Maximum attempts reached
# =====================================

def test_max_attempts_reached():

    fake_client = Mock()

    fake_client.models.generate_content.side_effect = [
        errors.APIError(503, {"error": {"message": "Service Unavailable"}}),
        errors.APIError(503, {"error": {"message": "Service Unavailable"}}),
        errors.APIError(503, {"error": {"message": "Service Unavailable"}})
    ]

    with patch("gemini_client.time.sleep") as mocked_sleep, \
         patch(
             "gemini_client.random.uniform",
             side_effect=[0.75, 1.5]
         ) as mocked_random:

        with pytest.raises(errors.APIError) as error:

            generate_response(
                client=fake_client,
                model="fake-model",
                prompt="Test prompt"
            )

    assert error.value.code == 503

    assert fake_client.models.generate_content.call_count == 3

    assert mocked_random.call_args_list == [
        call(0, 1),
        call(0, 2)
    ]

    assert mocked_sleep.call_args_list == [
        call(0.75),
        call(1.5)
    ]

    print("\nTEST 2 PASSED: Original APIError preserved after maximum attempts.")


# =====================================
# TEST 3: Non-Retryable Error
# =====================================

def test_non_retryable_error():

    fake_client = Mock()

    fake_client.models.generate_content.side_effect = errors.APIError(
        401,
        {"error": {"message": "Unauthorized"}}
    )

    with patch("gemini_client.time.sleep") as mocked_sleep:

        with pytest.raises(errors.APIError) as error:

            generate_response(
                client=fake_client,
                model="fake-model",
                prompt="Test prompt"
            )

    assert error.value.code == 401
    assert fake_client.models.generate_content.call_count == 1
    assert mocked_sleep.call_count == 0

    print("\nTEST 3 PASSED: Non-retryable error handled correctly.")


# =====================================
# TEST 4: Invalid max_attempts
# =====================================

@pytest.mark.parametrize(
    "invalid_attempts",
    [0, -1, 1.5, True]
)
def test_invalid_max_attempts(invalid_attempts):

    fake_client = Mock()

    with pytest.raises(
        ValueError,
        match="max_attempts must be a positive integer"
    ):

        generate_response(
            client=fake_client,
            model="fake-model",
            prompt="Test prompt",
            max_attempts=invalid_attempts
        )

    fake_client.models.generate_content.assert_not_called()

    print(
        f"\nTEST 4 PASSED: Invalid max_attempts rejected: "
        f"{invalid_attempts}"
    )


# =====================================
# TEST 5: Retry-After in Seconds
# =====================================

def test_retry_after_seconds():

    fake_client = Mock()

    api_error = create_api_error(429, "5")

    successful_response = Mock()
    successful_response.text = "Request succeeded!"

    fake_client.models.generate_content.side_effect = [
        api_error,
        successful_response
    ]

    with patch("gemini_client.time.sleep") as mocked_sleep:

        result = generate_response(
            client=fake_client,
            model="fake-model",
            prompt="Test prompt"
        )

    assert result == "Request succeeded!"
    assert fake_client.models.generate_content.call_count == 2
    mocked_sleep.assert_called_once_with(5.0)

    print("\nTEST 5 PASSED: Retry-After seconds handled correctly.")


# =====================================
# TEST 6: Retry-After HTTP Date
# =====================================

def test_retry_after_http_date():

    future_date = datetime.now(timezone.utc) + timedelta(seconds=20)

    retry_after = format_datetime(future_date, usegmt=True)

    api_error = create_api_error(503, retry_after)

    delay = get_retry_after_seconds(api_error)

    assert delay is not None
    assert 17 < delay <= 20

    print("\nTEST 6 PASSED: Retry-After HTTP date parsed correctly.")


# =====================================
# TEST 7: Invalid Retry-After
# =====================================

def test_invalid_retry_after_uses_backoff():

    fake_client = Mock()

    api_error = create_api_error(503, "invalid-value")

    successful_response = Mock()
    successful_response.text = "Request succeeded!"

    fake_client.models.generate_content.side_effect = [
        api_error,
        successful_response
    ]

    with patch("gemini_client.time.sleep") as mocked_sleep, \
         patch("gemini_client.random.uniform", return_value=0.5) as mocked_random:

        result = generate_response(
            client=fake_client,
            model="fake-model",
            prompt="Test prompt"
        )

    assert result == "Request succeeded!"

    mocked_random.assert_called_once_with(0, 1)
    mocked_sleep.assert_called_once_with(0.5)

    print("\nTEST 7 PASSED: Invalid Retry-After falls back to backoff.")


# =====================================
# TEST 8: Retry-After Exceeds Maximum
# =====================================

def test_retry_after_exceeds_maximum():

    fake_client = Mock()

    api_error = create_api_error(429, "60")

    fake_client.models.generate_content.side_effect = api_error

    with patch("gemini_client.time.sleep") as mocked_sleep:

        with pytest.raises(errors.APIError) as error:

            generate_response(
                client=fake_client,
                model="fake-model",
                prompt="Test prompt"
            )

    assert error.value is api_error
    assert fake_client.models.generate_content.call_count == 1
    mocked_sleep.assert_not_called()

    print("\nTEST 8 PASSED: Excessive Retry-After stops retries.")


# =====================================
# RUN ALL TESTS
# =====================================

if __name__ == "__main__":

    pytest.main([__file__, "-v"])
