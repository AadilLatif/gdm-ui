import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

from fgc_core.services.auth_service import decode_token, hash_password


class TestAuthLogic:
    def test_decode_token_returns_none_for_invalid_token(self):
        result = decode_token("invalid.token.string")
        assert result is None

    @patch("fgc_core.services.auth_service.settings")
    def test_decode_token_returns_payload_for_valid_token(self, mock_settings):
        mock_settings.secret_key = "test-secret-key-123"
        mock_settings.algorithm = "HS256"

        password = "test_password"
        hashed = hash_password(password)

        mock_settings.secret_key = "test-secret-key-123"
        mock_settings.algorithm = "HS256"
        mock_settings.access_token_expire_minutes = 60

        from fgc_core.services.auth_service import create_access_token
        token = create_access_token({"sub": "user-123", "type": "access"})

        result = decode_token(token)
        assert result is not None
        assert result["sub"] == "user-123"
        assert result["type"] == "access"

    @patch("fgc_core.services.auth_service.settings")
    def test_decode_token_returns_none_for_wrong_type(self, mock_settings):
        mock_settings.secret_key = "test-secret-key-123"
        mock_settings.algorithm = "HS256"
        mock_settings.refresh_token_expire_days = 7

        from fgc_core.services.auth_service import create_refresh_token
        token = create_refresh_token({"sub": "user-123", "type": "refresh"})

        result = decode_token(token)
        assert result is not None
        assert result["type"] == "refresh"


class TestAdminCheck:
    def test_admin_user_passes_check(self):
        admin_user = MagicMock()
        admin_user.is_admin = True

        from fgc_core.dependencies import get_admin_user
        import asyncio

        async def run_test():
            result = await get_admin_user(admin_user)
            return result

        result = asyncio.get_event_loop().run_until_complete(run_test())
        assert result.is_admin is True

    def test_non_admin_raises_403(self):
        regular_user = MagicMock()
        regular_user.is_admin = False

        from fgc_core.dependencies import get_admin_user
        import asyncio

        async def run_test():
            with pytest.raises(HTTPException) as exc_info:
                await get_admin_user(regular_user)
            return exc_info.value

        exc = asyncio.get_event_loop().run_until_complete(run_test())
        assert exc.status_code == 403