import pytest
from pydantic import ValidationError

from fgc_core.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    RefreshRequest,
)
from fgc_core.schemas.user import UserResponse, UserUpdate
from fgc_core.schemas.project import ProjectResponse, ProjectUpdate


class TestRegisterRequest:
    def test_valid_registration(self):
        req = RegisterRequest(
            email="user@example.com",
            username="testuser",
            password="securepassword123",
        )
        assert req.email == "user@example.com"
        assert req.username == "testuser"
        assert req.password == "securepassword123"

    def test_invalid_email(self):
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="not-an-email",
                username="testuser",
                password="password",
            )

    def test_empty_password(self):
        req = RegisterRequest(
            email="user@example.com",
            username="testuser",
            password="",
        )
        assert req.password == ""


class TestLoginRequest:
    def test_valid_login(self):
        req = LoginRequest(username="testuser", password="password123")
        assert req.username == "testuser"
        assert req.password == "password123"

    def test_missing_username(self):
        with pytest.raises(ValidationError):
            LoginRequest(password="password123")

    def test_missing_password(self):
        with pytest.raises(ValidationError):
            LoginRequest(username="testuser")


class TestTokenResponse:
    def test_default_token_type(self):
        resp = TokenResponse(
            access_token="access_token_value",
            refresh_token="refresh_token_value",
        )
        assert resp.token_type == "bearer"

    def test_custom_token_type(self):
        resp = TokenResponse(
            access_token="access_token_value",
            refresh_token="refresh_token_value",
            token_type="custom",
        )
        assert resp.token_type == "custom"


class TestRefreshRequest:
    def test_valid_refresh_request(self):
        req = RefreshRequest(refresh_token="some_refresh_token")
        assert req.refresh_token == "some_refresh_token"


class TestUserResponse:
    def test_valid_user_response(self):
        from datetime import datetime, timezone

        resp = UserResponse(
            id="user-123",
            email="user@example.com",
            username="testuser",
            is_active=True,
            is_admin=False,
            created_at=datetime.now(timezone.utc),
        )
        assert resp.id == "user-123"
        assert resp.email == "user@example.com"

    def test_user_response_from_attributes(self):
        from datetime import datetime, timezone

        mock_user = type("MockUser", (), {
            "id": "user-456",
            "email": "admin@example.com",
            "username": "admin",
            "is_active": True,
            "is_admin": True,
            "created_at": datetime.now(timezone.utc),
        })()

        resp = UserResponse.model_validate(mock_user)
        assert resp.id == "user-456"
        assert resp.username == "admin"
        assert resp.is_admin is True


class TestUserUpdate:
    def test_all_optional_fields(self):
        update = UserUpdate()
        assert update.email is None
        assert update.username is None
        assert update.is_active is None

    def test_partial_update(self):
        update = UserUpdate(email="new@example.com")
        assert update.email == "new@example.com"
        assert update.username is None

    def test_multiple_fields(self):
        update = UserUpdate(
            email="new@example.com",
            username="newname",
            is_active=False,
        )
        assert update.email == "new@example.com"
        assert update.username == "newname"
        assert update.is_active is False


class TestProjectResponse:
    def test_valid_project_response(self):
        from datetime import datetime, timezone

        resp = ProjectResponse(
            id="proj-123",
            name="Test Project",
            description="A test project",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            owner_id="user-123",
        )
        assert resp.name == "Test Project"
        assert resp.is_active is True

    def test_project_response_from_attributes(self):
        from datetime import datetime, timezone

        mock_project = type("MockProject", (), {
            "id": "proj-456",
            "name": "Another Project",
            "description": "Description here",
            "is_active": False,
            "created_at": datetime.now(timezone.utc),
            "owner_id": "user-456",
        })()

        resp = ProjectResponse.model_validate(mock_project)
        assert resp.name == "Another Project"


class TestProjectUpdate:
    def test_all_optional(self):
        update = ProjectUpdate()
        assert update.name is None
        assert update.description is None

    def test_update_name_only(self):
        update = ProjectUpdate(name="New Name")
        assert update.name == "New Name"

    def test_update_description_only(self):
        update = ProjectUpdate(description="New description")
        assert update.description == "New description"

    def test_update_both(self):
        update = ProjectUpdate(
            name="New Name",
            description="New description",
        )
        assert update.name == "New Name"
        assert update.description == "New description"