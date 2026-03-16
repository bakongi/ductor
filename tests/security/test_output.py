"""Tests for output sanitization: output.py."""

from __future__ import annotations

import pytest

from ductor_bot.security.output import sanitize_output


# ---------------------------------------------------------------------------
# ENV_VAR=value patterns
# ---------------------------------------------------------------------------


class TestEnvVarSecrets:
    @pytest.mark.parametrize(
        "text",
        [
            "API_KEY=abc123secret",
            "MY_API_KEY=some-value",
            "OPENAI_APIKEY=sk-test123",
            "TOKEN=mysecrettoken123",
            "SECRET=verysecret",
            "PASSWORD=hunter2",
            "DB_PASS=mypassword",
            "AWS_CREDENTIAL=AKIA1234567890",
            "AUTH_TOKEN=bearer-value",
            "api_key=lowercase_too",
            "My-Api-Key=dashed",
        ],
    )
    def test_env_var_redacted(self, text: str) -> None:
        assert "[REDACTED]" in sanitize_output(text)

    def test_surrounding_text_preserved(self) -> None:
        text = "Config loaded: API_KEY=secret123 successfully"
        result = sanitize_output(text)
        assert "Config loaded:" in result
        assert "secret123" not in result
        assert "[REDACTED]" in result


# ---------------------------------------------------------------------------
# OpenAI API keys
# ---------------------------------------------------------------------------


class TestOpenAIKeys:
    def test_openai_key_redacted(self) -> None:
        text = "Using key sk-abcdefghijklmnopqrstuvwx"
        result = sanitize_output(text)
        assert "sk-abcdefghijklmnopqrstuvwx" not in result
        assert "[REDACTED]" in result

    def test_short_sk_not_redacted(self) -> None:
        text = "The sk-short prefix is fine"
        assert sanitize_output(text) == text


# ---------------------------------------------------------------------------
# Anthropic API keys
# ---------------------------------------------------------------------------


class TestAnthropicKeys:
    def test_anthropic_key_redacted(self) -> None:
        text = "Key: sk-ant-abcdefghijklmnopqrstuvwx"
        result = sanitize_output(text)
        assert "sk-ant-abcdefghijklmnopqrstuvwx" not in result
        assert "[REDACTED]" in result


# ---------------------------------------------------------------------------
# GitHub tokens
# ---------------------------------------------------------------------------


class TestGitHubTokens:
    def test_github_pat_redacted(self) -> None:
        token = "ghp_" + "A" * 36
        text = f"Using token {token}"
        result = sanitize_output(text)
        assert token not in result
        assert "[REDACTED]" in result

    def test_short_ghp_not_redacted(self) -> None:
        text = "The ghp_short prefix"
        assert sanitize_output(text) == text


# ---------------------------------------------------------------------------
# Telegram bot tokens
# ---------------------------------------------------------------------------


class TestTelegramTokens:
    def test_telegram_token_redacted(self) -> None:
        text = "Bot token: 123456789:ABCDefgh-IJKLmnop_QRSTuvwx012345678"
        result = sanitize_output(text)
        assert "123456789:ABCDefgh" not in result
        assert "[REDACTED]" in result

    def test_normal_numbers_not_redacted(self) -> None:
        text = "The number 123456789 is just a number"
        assert sanitize_output(text) == text


# ---------------------------------------------------------------------------
# Bearer tokens
# ---------------------------------------------------------------------------


class TestBearerTokens:
    def test_bearer_token_redacted(self) -> None:
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.payload"
        result = sanitize_output(text)
        assert "eyJhbGciOiJIUzI1NiJ9" not in result
        assert "[REDACTED]" in result


# ---------------------------------------------------------------------------
# Multiple secrets
# ---------------------------------------------------------------------------


class TestMultipleSecrets:
    def test_multiple_secrets_all_redacted(self) -> None:
        text = (
            "API_KEY=secret1 TOKEN=secret2\n"
            "Bearer eyJhbGciOiJIUzI1NiJ9.test.signature\n"
            "ghp_" + "B" * 36
        )
        result = sanitize_output(text)
        assert "secret1" not in result
        assert "secret2" not in result
        assert "eyJhbGciOiJIUzI1NiJ9" not in result
        assert result.count("[REDACTED]") >= 3


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_string(self) -> None:
        assert sanitize_output("") == ""

    def test_short_string(self) -> None:
        assert sanitize_output("hello") == "hello"

    def test_no_secrets(self) -> None:
        text = "This is a perfectly normal response with no secrets at all."
        assert sanitize_output(text) == text

    def test_whitespace_only(self) -> None:
        text = "          \n\n\t\t"
        assert sanitize_output(text) == text


# ---------------------------------------------------------------------------
# False positive resistance
# ---------------------------------------------------------------------------


class TestFalsePositives:
    @pytest.mark.parametrize(
        "text",
        [
            "The password field is required for login.",
            "Set the token_expiry to 3600 seconds.",
            "Authentication is handled by the auth module.",
            "The secret to good code is simplicity.",
            "Use a bearer of good news.",
            "The GitHub project has 36 contributors.",
        ],
    )
    def test_benign_text_preserved(self, text: str) -> None:
        assert sanitize_output(text) == text
