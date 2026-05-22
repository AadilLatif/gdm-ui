import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from jose import jwt

from fgc_core.services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)


class TestHashPassword:
    def test_hash_password_returns_string(self):
        result = hash_password("testpassword123")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_hash_password_different_each_time(self):
        hash1 = hash_password("password")
        hash2 = hash_password("password")
        assert hash1 != hash2

    def test_hash_password_unicode(self):
        result = hash_password("пароль日本語")
        assert isinstance(result, str)


class TestVerifyPassword:
    def test_verify_password_correct(self):
        password = "my_secure_password"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        password = "my_secure_password"
        hashed = hash_password(password)
        assert verify_password("wrong_password", hashed) is False

    def test_verify_password_empty(self):
        hashed = hash_password("password")
        assert verify_password("", hashed) is False


class TestCreateAccessToken:
    @patch("fgc_core.services.auth_service.settings")
    def test_create_access_token_returns_string(self, mock_settings):
        mock_settings.secret_key = "test-secret"
        mock_settings.algorithm = "HS256"
        mock_settings.access_token_expire_minutes = 60

        result = create_access_token({"sub": "user123"})
        assert isinstance(result, str)
        assert len(result) > 0

    @patch("fgc_core.services.auth_service.settings")
    def test_create_access_token_contains_type(self, mock_settings):
        mock_settings.secret_key = "test-secret"
        mock_settings.algorithm = "HS256"
        mock_settings.access_token_expire_minutes = 60

        token = create_access_token({"sub": "user123"})
        decoded = jwt.decode(token, "test-secret", algorithms=["HS256"])
        assert decoded["type"] == "access"

    @patch("fgc_core.services.auth_service.settings")
    def test_create_access_token_contains_subject(self, mock_settings):
        mock_settings.secret_key = "test-secret"
        mock_settings.algorithm = "HS256"
        mock_settings.access_token_expire_minutes = 60

        token = create_access_token({"sub": "user123"})
        decoded = jwt.decode(token, "test-secret", algorithms=["HS256"])
        assert decoded["sub"] == "user123"

    @patch("fgc_core.services.auth_service.settings")
    def test_create_access_token_has_expiry(self, mock_settings):
        mock_settings.secret_key = "test-secret"
        mock_settings.algorithm = "HS256"
        mock_settings.access_token_expire_minutes = 60

        token = create_access_token({"sub": "user123"})
        decoded = jwt.decode(token, "test-secret", algorithms=["HS256"])
        assert "exp" in decoded


class TestCreateRefreshToken:
    @patch("fgc_core.services.auth_service.settings")
    def test_create_refresh_token_returns_string(self, mock_settings):
        mock_settings.secret_key = "test-secret"
        mock_settings.algorithm = "HS256"
        mock_settings.refresh_token_expire_days = 7

        result = create_refresh_token({"sub": "user123"})
        assert isinstance(result, str)
        assert len(result) > 0

    @patch("fgc_core.services.auth_service.settings")
    def test_create_refresh_token_contains_type(self, mock_settings):
        mock_settings.secret_key = "test-secret"
        mock_settings.algorithm = "HS256"
        mock_settings.refresh_token_expire_days = 7

        token = create_refresh_token({"sub": "user123"})
        decoded = jwt.decode(token, "test-secret", algorithms=["HS256"])
        assert decoded["type"] == "refresh"


class TestDecodeToken:
    @patch("fgc_core.services.auth_service.settings")
    def test_decode_valid_token(self, mock_settings):
        mock_settings.secret_key = "test-secret"
        mock_settings.algorithm = "HS256"
        mock_settings.access_token_expire_minutes = 60

        token = create_access_token({"sub": "user123"})
        result = decode_token(token)
        assert result is not None
        assert result["sub"] == "user123"

    @patch("fgc_core.services.auth_service.settings")
    def test_decode_invalid_token(self, mock_settings):
        mock_settings.secret_key = "test-secret"
        mock_settings.algorithm = "HS256"

        result = decode_token("invalid.token.here")
        assert result is None

    @patch("fgc_core.services.auth_service.settings")
    def test_decode_expired_token(self, mock_settings):
        mock_settings.secret_key = "test-secret"
        mock_settings.algorithm = "HS256"

        expired_payload = {
            "sub": "user123",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            "type": "access",
        }
        token = jwt.encode(expired_payload, "test-secret", algorithm="HS256")
        result = decode_token(token)
        assert result is None

    def test_decode_empty_string(self):
        result = decode_token("")
        assert result is None