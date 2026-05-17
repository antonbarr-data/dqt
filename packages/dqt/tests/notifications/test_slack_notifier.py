import json
from unittest.mock import MagicMock, patch

from dqt.notifications.slack import SlackNotifier


def test_send_blocks_returns_false_when_no_webhook():
    notifier = SlackNotifier(webhook_url="")
    result = notifier.send_blocks([{"type": "section", "text": {"type": "mrkdwn", "text": "test"}}])
    assert result is False


def _mock_urlopen(status: int = 200):
    mock_resp = MagicMock()
    mock_resp.status = status
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


def test_send_blocks_posts_correct_payload():
    blocks = [{"type": "header", "text": {"type": "plain_text", "text": "dqt Daily Digest"}}]
    notifier = SlackNotifier(webhook_url="https://hooks.slack.com/fake")
    with patch("urllib.request.urlopen", return_value=_mock_urlopen()) as mock_open:
        result = notifier.send_blocks(blocks, text="daily digest")
    assert result is True
    request = mock_open.call_args[0][0]
    body = json.loads(request.data)
    assert body["blocks"] == blocks
    assert body["text"] == "daily digest"


def test_send_text_sends_empty_blocks():
    notifier = SlackNotifier(webhook_url="https://hooks.slack.com/fake")
    with patch("urllib.request.urlopen", return_value=_mock_urlopen()) as mock_open:
        notifier.send_text("hello world")
    body = json.loads(mock_open.call_args[0][0].data)
    assert body["text"] == "hello world"
    assert body["blocks"] == []


def test_send_blocks_returns_false_on_network_error():
    notifier = SlackNotifier(webhook_url="https://hooks.slack.com/fake")
    with patch("urllib.request.urlopen", side_effect=Exception("network error")):
        assert notifier.send_blocks([]) is False


def test_uses_env_var_when_no_webhook_passed(monkeypatch):
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/env")
    notifier = SlackNotifier()
    assert notifier.webhook_url == "https://hooks.slack.com/env"
