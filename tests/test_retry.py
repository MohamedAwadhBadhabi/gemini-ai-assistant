
from unittest.mock import Mock, patch

from google.genai import errors

from gemini_client import generate_response


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

    with patch("gemini_client.time.sleep") as mocked_sleep:

        result = generate_response(
            client=fake_client,
            model="fake-model",
            prompt="Test prompt"
        )

    assert result == "Gemini request succeeded!"
    assert fake_client.models.generate_content.call_count == 2
    assert mocked_sleep.call_count == 1

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

    with patch("gemini_client.time.sleep") as mocked_sleep:

        try:
            generate_response(
                client=fake_client,
                model="fake-model",
                prompt="Test prompt"
            )

        except RuntimeError as error:

            assert "Maximum retry attempts reached" in str(error)

        else:
            raise AssertionError("Expected RuntimeError was not raised.")

    assert fake_client.models.generate_content.call_count == 3
    assert mocked_sleep.call_count == 2

    print("\nTEST 2 PASSED: Maximum attempts handled correctly.")


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

        try:
            generate_response(
                client=fake_client,
                model="fake-model",
                prompt="Test prompt"
            )

        except errors.APIError as error:

            assert error.code == 401

        else:
            raise AssertionError("Expected APIError was not raised.")

    assert fake_client.models.generate_content.call_count == 1
    assert mocked_sleep.call_count == 0

    print("\nTEST 3 PASSED: Non-retryable error handled correctly.")


# =====================================
# RUN ALL TESTS
# =====================================

if __name__ == "__main__":

    test_retry_success()
    test_max_attempts_reached()
    test_non_retryable_error()

    print("\nALL TESTS PASSED!")
