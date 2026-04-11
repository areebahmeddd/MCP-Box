import pytest
from pydantic import ValidationError

from superbox.shared.models import (
    AuthDevicePollRequest,
    AuthDeviceStartRequest,
    AuthLoginRequest,
    AuthProviderRequest,
    AuthRefreshRequest,
    AuthRegisterRequest,
    AuthResponse,
    AuthUpdateRequest,
    AuthUserProfile,
    CreateOrderRequest,
    CreateServerRequest,
    MCPServer,
    Meta,
    Pricing,
    Repository,
    ToolInfo,
    UpdateServerRequest,
    VerifyPaymentRequest,
)


class TestRepository:
    def test_valid_construction(self) -> None:
        repo = Repository(type="git", url="https://github.com/test/repo")
        assert repo.type == "git"
        assert repo.url == "https://github.com/test/repo"

    def test_missing_url_raises(self) -> None:
        with pytest.raises(ValidationError):
            Repository(type="git")  # type: ignore[call-arg]

    def test_missing_type_raises(self) -> None:
        with pytest.raises(ValidationError):
            Repository(url="https://github.com/test/repo")  # type: ignore[call-arg]


class TestPricing:
    def test_valid_pricing(self) -> None:
        p = Pricing(currency="INR", amount=999.0)
        assert p.currency == "INR"
        assert p.amount == pytest.approx(999.0)

    def test_free_pricing(self) -> None:
        p = Pricing(currency="USD", amount=0.0)
        assert p.amount == 0.0

    def test_missing_currency_raises(self) -> None:
        with pytest.raises(ValidationError):
            Pricing(amount=10.0)  # type: ignore[call-arg]


class TestToolInfo:
    def test_valid_tool_info(self) -> None:
        t = ToolInfo(count=2, names=["get_weather", "get_forecast"])
        assert t.count == 2
        assert "get_weather" in t.names

    def test_empty_names(self) -> None:
        t = ToolInfo(count=0, names=[])
        assert t.names == []


class TestMeta:
    def test_valid_meta(self) -> None:
        m = Meta(created_at="2025-01-01T00:00:00+00:00", updated_at="2025-06-01T00:00:00+00:00")
        assert "2025-01-01" in m.created_at

    def test_missing_created_at_raises(self) -> None:
        with pytest.raises(ValidationError):
            Meta(updated_at="2025-01-01T00:00:00+00:00")  # type: ignore[call-arg]


class TestMCPServer:
    def test_full_construction(self, sample_server: dict) -> None:
        server = MCPServer(**sample_server)
        assert server.name == "weather-mcp"
        assert server.lang == "python"
        assert server.repository.url == "https://github.com/test/weather-mcp"

    def test_optional_fields_default_to_none(self) -> None:
        server = MCPServer(
            name="minimal",
            version="1.0.0",
            description="desc",
            author="auth",
            lang="python",
            license="MIT",
            entrypoint="main.py",
            repository=Repository(type="git", url="https://github.com/a/b"),
        )
        assert server.pricing is None
        assert server.security_report is None
        assert server.meta is None
        assert server.tools is None

    def test_pricing_nested_model_accepted(self, sample_server: dict) -> None:
        server = MCPServer(**sample_server)
        assert server.pricing is not None
        assert server.pricing.currency == "INR"

    def test_missing_name_raises(self) -> None:
        with pytest.raises(ValidationError):
            MCPServer(  # type: ignore[call-arg]
                version="1.0.0",
                description="x",
                author="x",
                lang="python",
                license="MIT",
                entrypoint="main.py",
                repository={"type": "git", "url": "https://github.com/a/b"},
            )

    def test_repository_accepts_dict(self) -> None:
        server = MCPServer(
            name="s",
            version="1.0.0",
            description="d",
            author="a",
            lang="python",
            license="MIT",
            entrypoint="main.py",
            repository={"type": "git", "url": "https://github.com/a/b"},
        )
        assert server.repository.type == "git"


class TestCreateServerRequest:
    def test_valid_request(self) -> None:
        req = CreateServerRequest(
            name="test",
            version="1.0.0",
            description="desc",
            author="auth",
            lang="python",
            license="MIT",
            entrypoint="main.py",
            repository=Repository(type="git", url="https://github.com/a/b"),
            pricing=Pricing(currency="INR", amount=0.0),
        )
        assert req.name == "test"
        assert req.pricing.amount == 0.0

    def test_tools_optional(self) -> None:
        req = CreateServerRequest(
            name="test",
            version="1.0.0",
            description="desc",
            author="auth",
            lang="python",
            license="MIT",
            entrypoint="main.py",
            repository=Repository(type="git", url="https://github.com/a/b"),
            pricing=Pricing(currency="INR", amount=0.0),
        )
        assert req.tools is None


class TestUpdateServerRequest:
    def test_all_fields_optional(self) -> None:
        req = UpdateServerRequest()
        assert req.name is None
        assert req.version is None
        assert req.description is None
        assert req.security_report is None

    def test_partial_update(self) -> None:
        req = UpdateServerRequest(name="updated", version="2.0.0")
        assert req.name == "updated"
        assert req.version == "2.0.0"
        assert req.description is None

    def test_repository_dict_accepted(self) -> None:
        req = UpdateServerRequest(repository={"type": "git", "url": "https://github.com/a/b"})
        assert req.repository.url == "https://github.com/a/b"


class TestAuthModels:
    def test_register_request_valid(self) -> None:
        req = AuthRegisterRequest(email="user@example.com", password="secret123")
        assert req.email == "user@example.com"
        assert req.display_name is None

    def test_register_request_with_display_name(self) -> None:
        req = AuthRegisterRequest(email="user@example.com", password="secret", display_name="Alice")
        assert req.display_name == "Alice"

    def test_register_request_invalid_email_raises(self) -> None:
        with pytest.raises(ValidationError):
            AuthRegisterRequest(email="not-an-email", password="secret")

    def test_login_request_valid(self) -> None:
        req = AuthLoginRequest(email="user@example.com", password="pass")
        assert req.password == "pass"

    def test_login_request_invalid_email_raises(self) -> None:
        with pytest.raises(ValidationError):
            AuthLoginRequest(email="bad", password="pw")

    def test_provider_request_valid(self) -> None:
        req = AuthProviderRequest(provider="google")
        assert req.provider == "google"
        assert req.id_token is None
        assert req.access_token is None

    def test_device_start_request(self) -> None:
        req = AuthDeviceStartRequest(provider="github")
        assert req.provider == "github"

    def test_device_poll_request(self) -> None:
        req = AuthDevicePollRequest(device_code="code-abc")
        assert req.device_code == "code-abc"

    def test_refresh_request(self) -> None:
        req = AuthRefreshRequest(refresh_token="ref-tok")
        assert req.refresh_token == "ref-tok"

    def test_update_request_all_optional(self) -> None:
        req = AuthUpdateRequest()
        assert req.display_name is None
        assert req.password is None

    def test_auth_response(self) -> None:
        resp = AuthResponse(
            id_token="id-tok",
            refresh_token="ref-tok",
            expires_in=3600,
            email="u@x.com",
            local_id="uid-1",
        )
        assert resp.id_token == "id-tok"
        assert resp.expires_in == 3600

    def test_auth_user_profile(self) -> None:
        profile = AuthUserProfile(local_id="uid-1", email="u@x.com", email_verified=True)
        assert profile.local_id == "uid-1"
        assert profile.email_verified is True
        assert profile.disabled is False


class TestPaymentModels:
    def test_create_order_request(self) -> None:
        req = CreateOrderRequest(server_name="weather-mcp", amount=9.99, currency="INR")
        assert req.server_name == "weather-mcp"
        assert req.currency == "INR"
        assert req.amount == pytest.approx(9.99)

    def test_verify_payment_request(self) -> None:
        req = VerifyPaymentRequest(
            razorpay_order_id="order_123",
            razorpay_payment_id="pay_456",
            razorpay_signature="sig_789",
            server_name="weather-mcp",
        )
        assert req.razorpay_order_id == "order_123"
        assert req.razorpay_payment_id == "pay_456"
        assert req.razorpay_signature == "sig_789"
        assert req.server_name == "weather-mcp"

    def test_create_order_missing_amount_raises(self) -> None:
        with pytest.raises(ValidationError):
            CreateOrderRequest(server_name="x", currency="INR")  # type: ignore[call-arg]
