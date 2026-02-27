import pytest
from pydantic import ValidationError

from superbox.shared.models import (
    AuthLoginRequest,
    AuthRegisterRequest,
    CreateOrderRequest,
    CreateServerRequest,
    MCPServer,
    Pricing,
    Repository,
    VerifyPaymentRequest,
)


class TestRepository:
    def test_valid_repository(self) -> None:
        repo = Repository(type="git", url="https://github.com/test/repo")
        assert repo.type == "git"
        assert repo.url == "https://github.com/test/repo"

    def test_missing_url_raises(self) -> None:
        with pytest.raises(ValidationError):
            Repository(type="git")  # type: ignore[call-arg]


class TestPricing:
    def test_valid_pricing(self) -> None:
        p = Pricing(currency="INR", amount=999.0)
        assert p.currency == "INR"
        assert p.amount == pytest.approx(999.0)

    def test_free_pricing(self) -> None:
        p = Pricing(currency="INR", amount=0.0)
        assert p.amount == 0.0


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

    def test_pricing_accepted(self, sample_server: dict) -> None:
        server = MCPServer(**sample_server)
        assert server.pricing is not None
        assert server.pricing.currency == "INR"

    def test_missing_required_field_raises(self) -> None:
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


class TestAuthModels:
    def test_register_request_valid_email(self) -> None:
        req = AuthRegisterRequest(email="user@example.com", password="secret123")
        assert req.email == "user@example.com"

    def test_register_request_invalid_email(self) -> None:
        with pytest.raises(ValidationError):
            AuthRegisterRequest(email="not-an-email", password="secret")

    def test_login_request(self) -> None:
        req = AuthLoginRequest(email="user@example.com", password="pass")
        assert req.password == "pass"


class TestPaymentModels:
    def test_create_order_request(self) -> None:
        req = CreateOrderRequest(server_name="weather-mcp", amount=9.99, currency="INR")
        assert req.server_name == "weather-mcp"
        assert req.currency == "INR"

    def test_verify_payment_request(self) -> None:
        req = VerifyPaymentRequest(
            razorpay_order_id="order_123",
            razorpay_payment_id="pay_456",
            razorpay_signature="sig_789",
            server_name="weather-mcp",
        )
        assert req.razorpay_order_id == "order_123"
