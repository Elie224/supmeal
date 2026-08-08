import pytest

from app.api.v1.endpoints import _oauth_codes
from app.core import email_verification
from app.core import mailer as mailer_module
from app.core.config import Settings
from app.core.mailer import MailerError, is_smtp_configured, send_email_verification
from app.core.ratelimit import InMemoryRateLimiter, IPRateLimit
from app.core.security import create_access_token, decode_access_token, verify_password
from app.core.security_utils import (
    is_safe_username,
    safe_image_extension,
    sanitize_csv_cell,
    sniff_image,
    strip_html,
)


def test_sniff_image_formats_and_invalid_data():
    assert sniff_image(b"") is None
    assert sniff_image(b"abc") is None

    assert sniff_image(b"\x89PNG\r\n\x1a\nDATA") == ".png"
    assert sniff_image(b"\xff\xd8\xff" + b"x" * 8) == ".jpg"
    assert sniff_image(b"GIF87a" + b"x" * 8) == ".gif"
    assert sniff_image(b"GIF89a" + b"x" * 8) == ".gif"
    assert sniff_image(b"RIFF1234WEBPxxxx") == ".webp"

    assert sniff_image(b"not-an-image-data") is None


def test_sniff_image_rejects_oversized_file():
    oversized = b"x" * (10 * 1024 * 1024 + 1)
    assert sniff_image(oversized) is None


def test_safe_image_extension():
    assert safe_image_extension(".jpg", ".jpg") == ".jpg"
    assert safe_image_extension(".jpeg", ".jpg") == ".jpg"
    assert safe_image_extension(".png", ".png") == ".png"

    # On fait confiance aux magic bytes plutot qu'a l'extension declaree.
    assert safe_image_extension(".jpg", ".png") == ".png"
    assert safe_image_extension(".exe", ".png") == ".png"


def test_csv_sanitization():
    assert sanitize_csv_cell(None) == ""
    assert sanitize_csv_cell("bonjour") == "bonjour"

    assert sanitize_csv_cell("=1+1") == "'=1+1"
    assert sanitize_csv_cell("+cmd") == "'+cmd"
    assert sanitize_csv_cell("-10") == "'-10"
    assert sanitize_csv_cell("@formula") == "'@formula"


def test_username_validation():
    assert is_safe_username("elie_224") is True
    assert is_safe_username("abc") is True

    assert is_safe_username("ab") is False
    assert is_safe_username("nom avec espace") is False
    assert is_safe_username("<script>") is False


def test_strip_html():
    assert strip_html(None) == ""
    assert strip_html("") == ""
    assert strip_html("<b>Bonjour</b>") == "Bonjour"
    assert strip_html("  <script>alert(1)</script> Texte  ") == "alert(1) Texte"


def test_oauth_code_is_single_use():
    _oauth_codes._codes.clear()

    _oauth_codes.store_code("code-test", "token-test", ttl=60)

    assert _oauth_codes.consume_code("code-test") == "token-test"
    assert _oauth_codes.consume_code("code-test") is None


def test_oauth_code_expiration(monkeypatch):
    _oauth_codes._codes.clear()

    now = [1000.0]
    monkeypatch.setattr(_oauth_codes.time, "time", lambda: now[0])

    _oauth_codes.store_code("expired", "token", ttl=10)

    now[0] = 1011.0

    assert _oauth_codes.consume_code("expired") is None
    assert "expired" not in _oauth_codes._codes


def test_email_verification_success_and_single_use(monkeypatch):
    email_verification._codes.clear()

    monkeypatch.setattr(
        email_verification.secrets,
        "randbelow",
        lambda _: 123,
    )

    code = email_verification.issue_code(
        "USER@example.com",
        ttl_seconds=60,
    )

    assert code == "000123"

    assert email_verification.consume_code(
        "user@example.com",
        "000123",
    ) is True

    assert email_verification.consume_code(
        "user@example.com",
        "000123",
    ) is False


def test_email_verification_wrong_code_and_attempt_limit(monkeypatch):
    email_verification._codes.clear()

    monkeypatch.setattr(
        email_verification.secrets,
        "randbelow",
        lambda _: 456789,
    )

    email_verification.issue_code(
        "attempt@example.com",
        ttl_seconds=60,
    )

    assert email_verification.consume_code(
        "attempt@example.com",
        "000000",
        max_attempts=2,
    ) is False

    assert email_verification.consume_code(
        "attempt@example.com",
        "111111",
        max_attempts=2,
    ) is False

    # L'appel suivant depasse la limite et supprime le code.
    assert email_verification.consume_code(
        "attempt@example.com",
        "456789",
        max_attempts=2,
    ) is False

    assert "attempt@example.com" not in email_verification._codes


def test_email_verification_expiration(monkeypatch):
    email_verification._codes.clear()

    now = [2000.0]

    monkeypatch.setattr(
        email_verification.time,
        "time",
        lambda: now[0],
    )

    monkeypatch.setattr(
        email_verification.secrets,
        "randbelow",
        lambda _: 42,
    )

    email_verification.issue_code(
        "expire@example.com",
        ttl_seconds=10,
    )

    now[0] = 2011.0

    assert email_verification.consume_code(
        "expire@example.com",
        "000042",
    ) is False


def test_rate_limiters_reject_after_limit():
    limiter = InMemoryRateLimiter(
        max_requests=1,
        window_seconds=60,
    )

    assert limiter.is_allowed("user") is True
    assert limiter.is_allowed("user") is False

    ip_limiter = IPRateLimit(
        max_requests=1,
        window_seconds=60,
    )

    assert ip_limiter.is_allowed("127.0.0.1") is True
    assert ip_limiter.is_allowed("127.0.0.1") is False


def test_settings_cors_and_database_urls(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    settings = Settings(
        _env_file=None,
        app_env="test",
        backend_cors_origins="http://a.test, http://b.test, ,",
        DATABASE_URL=(
            "postgres://user:pass@localhost/db"
            "?sslmode=require&application_name=supmeal"
        ),
    )

    assert settings.cors_origins_list == [
        "http://a.test",
        "http://b.test",
    ]

    assert settings.database_url.startswith(
        "postgresql+asyncpg://"
    )

    assert "sslmode=" not in settings.database_url
    assert "application_name=supmeal" in settings.database_url

    assert settings.sync_database_url.startswith(
        "postgresql://"
    )


def test_default_database_urls(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    settings = Settings(
        _env_file=None,
        app_env="test",
        postgres_host="db",
        postgres_port=5432,
        postgres_db="supmeal_test",
        postgres_user="user",
        postgres_password="pass",
    )

    assert settings.database_url == (
        "postgresql+asyncpg://user:pass@db:5432/supmeal_test"
    )

    assert settings.sync_database_url == (
        "postgresql+psycopg2://user:pass@db:5432/supmeal_test"
    )


def test_production_rejects_insecure_secrets():
    with pytest.raises(ValueError):
        Settings(
            app_env="production",
            secret_key="CHANGE-ME",
            jwt_secret="CHANGE-ME",
        )


def test_security_invalid_password_hash_and_token():
    assert verify_password(
        "password",
        "not-a-valid-password-hash",
    ) is False

    assert decode_access_token(
        "this-is-not-a-valid-jwt"
    ) is None


def test_access_token_extra_payload():
    token = create_access_token(
        123,
        extra={"scope": "test-scope"},
    )

    payload = decode_access_token(token)

    assert payload is not None
    assert payload["sub"] == "123"
    assert payload["scope"] == "test-scope"
    assert payload["type"] == "access"


@pytest.mark.asyncio
async def test_mailer_rejects_missing_smtp():
    settings = Settings(
        app_env="test",
        smtp_host="",
        smtp_from_email="",
    )

    assert is_smtp_configured(settings) is False

    with pytest.raises(MailerError):
        await send_email_verification(
            settings,
            "dest@example.com",
            "123456",
        )


@pytest.mark.asyncio
async def test_mailer_smtp_starttls(monkeypatch):
    events = []

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            events.append(
                ("init", host, port, timeout)
            )

        def __enter__(self):
            return self

        def __exit__(
            self,
            exc_type,
            exc,
            traceback,
        ):
            return False

        def starttls(self, context):
            events.append(("starttls",))

        def login(self, username, password):
            events.append(
                ("login", username, password)
            )

        def send_message(self, message):
            events.append(
                (
                    "send",
                    message["To"],
                    message["Subject"],
                )
            )

    monkeypatch.setattr(
        mailer_module.smtplib,
        "SMTP",
        FakeSMTP,
    )

    settings = Settings(
        app_env="test",
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_username="user",
        smtp_password="secret",
        smtp_use_starttls=True,
        smtp_use_ssl=False,
        smtp_from_email="noreply@example.com",
        smtp_from_name="SUPMEAL",
    )

    assert is_smtp_configured(settings) is True

    await send_email_verification(
        settings,
        "dest@example.com",
        "123456",
    )

    assert (
        "init",
        "smtp.example.com",
        587,
        15,
    ) in events

    assert ("starttls",) in events

    assert (
        "login",
        "user",
        "secret",
    ) in events

    assert any(
        event[0] == "send"
        for event in events
    )


@pytest.mark.asyncio
async def test_mailer_smtp_ssl(monkeypatch):
    events = []

    class FakeSMTPSSL:
        def __init__(self, host, port, timeout):
            events.append(
                ("init_ssl", host, port, timeout)
            )

        def __enter__(self):
            return self

        def __exit__(
            self,
            exc_type,
            exc,
            traceback,
        ):
            return False

        def login(self, username, password):
            events.append(
                ("login", username, password)
            )

        def send_message(self, message):
            events.append(
                ("send_ssl", message["To"])
            )

    monkeypatch.setattr(
        mailer_module.smtplib,
        "SMTP_SSL",
        FakeSMTPSSL,
    )

    settings = Settings(
        app_env="test",
        smtp_host="smtp.example.com",
        smtp_port=465,
        smtp_username="",
        smtp_password="",
        smtp_use_starttls=False,
        smtp_use_ssl=True,
        smtp_from_email="noreply@example.com",
    )

    await send_email_verification(
        settings,
        "ssl@example.com",
        "654321",
    )

    assert (
        "init_ssl",
        "smtp.example.com",
        465,
        15,
    ) in events

    assert (
        "send_ssl",
        "ssl@example.com",
    ) in events
