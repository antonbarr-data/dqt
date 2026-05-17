from unittest.mock import MagicMock, patch

from dqt.notifications.email import EmailNotifier


def _mock_smtp():
    mock_server = MagicMock()
    mock_server.__enter__ = lambda s: s
    mock_server.__exit__ = MagicMock(return_value=False)
    return mock_server


def test_send_returns_true_on_success():
    notifier = EmailNotifier(host="localhost", port=1025, from_addr="dqt@test.com")
    mock_server = _mock_smtp()
    with patch("smtplib.SMTP", return_value=mock_server):
        result = notifier.send("alice@example.com", "Daily Digest", "<html>hi</html>", "hi")
    assert result is True


def test_send_uses_correct_addresses():
    notifier = EmailNotifier(host="localhost", port=1025, from_addr="dqt@test.com")
    mock_server = _mock_smtp()
    with patch("smtplib.SMTP", return_value=mock_server):
        notifier.send("bob@example.com", "Subject", "<p>body</p>", "body")
    from_addr, to_addrs, _ = mock_server.sendmail.call_args[0]
    assert from_addr == "dqt@test.com"
    assert "bob@example.com" in to_addrs


def test_send_includes_both_mime_parts():
    notifier = EmailNotifier(host="localhost", port=1025)
    mock_server = _mock_smtp()
    with patch("smtplib.SMTP", return_value=mock_server):
        notifier.send("alice@example.com", "Weekly", "<html>weekly</html>", "weekly plain")
    _, _, msg_str = mock_server.sendmail.call_args[0]
    assert "weekly plain" in msg_str
    assert "Weekly" in msg_str


def test_send_returns_false_on_smtp_error():
    notifier = EmailNotifier(host="localhost", port=1025)
    with patch("smtplib.SMTP", side_effect=Exception("connection refused")):
        assert notifier.send("alice@example.com", "Test", "<p>test</p>", "test") is False


def test_uses_env_vars(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "mail.example.com")
    monkeypatch.setenv("SMTP_PORT", "465")
    monkeypatch.setenv("SMTP_FROM", "noreply@example.com")
    notifier = EmailNotifier()
    assert notifier.host == "mail.example.com"
    assert notifier.port == 465
    assert notifier.from_addr == "noreply@example.com"
