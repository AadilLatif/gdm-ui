import pytest


@pytest.fixture
def sample_zip_content():
    import io
    import zipfile

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("test_system.json", '{"name": "Test System", "uuid": "12345678-1234-1234-1234-123456789012"}')
    buffer.seek(0)
    return buffer.read()


@pytest.fixture
def mock_user():
    from unittest.mock import MagicMock

    user = MagicMock()
    user.id = "test-user-id-123"
    user.email = "test@example.com"
    user.username = "testuser"
    user.is_active = True
    user.is_admin = False
    return user


@pytest.fixture
def mock_admin_user():
    from unittest.mock import MagicMock

    user = MagicMock()
    user.id = "admin-user-id-456"
    user.email = "admin@example.com"
    user.username = "admin"
    user.is_active = True
    user.is_admin = True
    return user