"""Canonical LLM layer: provider routing, degradation, and both backends (mocked)."""
from __future__ import annotations

import sys
import types

import pytest

from dqt.llm import get_llm

_ENV_KEYS = (
    "DQT_LLM_PROVIDER", "DQT_LLM_MAX_TOKENS", "DQT_LLM_TEMPERATURE", "DQT_LLM_TIMEOUT_SECONDS",
    "ANTHROPIC_API_KEY", "ANTHROPIC_MODEL",
    "LITELLM_MODEL", "LITELLM_API_BASE", "LITELLM_API_KEY",
    "OPENAI_API_KEY", "AZURE_API_KEY", "GEMINI_API_KEY", "COHERE_API_KEY", "MISTRAL_API_KEY",
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for k in _ENV_KEYS:
        monkeypatch.delenv(k, raising=False)


def _fake_anthropic(monkeypatch):
    """Install a fake `anthropic` module that records the create() kwargs."""
    calls = {}

    class _Msg:
        def __init__(self, text):
            self.content = [types.SimpleNamespace(text=text)]

    class _Messages:
        def create(self, **kwargs):
            calls["kwargs"] = kwargs
            return _Msg("  hello from claude  ")

    class _Anthropic:
        def __init__(self, **kwargs):
            calls["init"] = kwargs
            self.messages = _Messages()

    mod = types.ModuleType("anthropic")
    mod.Anthropic = _Anthropic
    monkeypatch.setitem(sys.modules, "anthropic", mod)
    return calls


def _fake_litellm(monkeypatch):
    calls = {}

    def completion(**kwargs):
        calls["kwargs"] = kwargs
        msg = types.SimpleNamespace(content="  hello from litellm  ")
        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=msg)])

    mod = types.ModuleType("litellm")
    mod.completion = completion
    monkeypatch.setitem(sys.modules, "litellm", mod)
    return calls


def test_default_provider_is_anthropic(monkeypatch):
    calls = _fake_anthropic(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-x")
    llm = get_llm()
    assert llm is not None
    assert llm.model == "claude-x"
    out = llm.complete([{"role": "user", "content": "hi"}], system="be brief", max_tokens=99)
    assert out == "hello from claude"  # stripped
    assert calls["kwargs"]["model"] == "claude-x"
    assert calls["kwargs"]["max_tokens"] == 99
    assert calls["kwargs"]["system"] == "be brief"
    assert calls["kwargs"]["messages"] == [{"role": "user", "content": "hi"}]


def test_anthropic_unconfigured_returns_none(monkeypatch):
    monkeypatch.setenv("DQT_LLM_PROVIDER", "anthropic")
    assert get_llm() is None


def test_litellm_routing_and_system_prepend(monkeypatch):
    calls = _fake_litellm(monkeypatch)
    monkeypatch.setenv("DQT_LLM_PROVIDER", "litellm")
    monkeypatch.setenv("LITELLM_MODEL", "gpt-4o")
    monkeypatch.setenv("LITELLM_API_KEY", "sk-proxy")
    monkeypatch.setenv("LITELLM_API_BASE", "http://localhost:4000")
    llm = get_llm()
    assert llm is not None and llm.model == "gpt-4o"
    out = llm.complete([{"role": "user", "content": "hi"}], system="sys")
    assert out == "hello from litellm"
    kw = calls["kwargs"]
    assert kw["model"] == "gpt-4o"
    assert kw["api_base"] == "http://localhost:4000"
    assert kw["api_key"] == "sk-proxy"
    assert kw["custom_llm_provider"] == "litellm_proxy"  # api_base => proxy routing
    # system prepended as a message
    assert kw["messages"][0] == {"role": "system", "content": "sys"}
    assert kw["messages"][1] == {"role": "user", "content": "hi"}


def test_litellm_configured_via_native_key(monkeypatch):
    calls = _fake_litellm(monkeypatch)
    monkeypatch.setenv("DQT_LLM_PROVIDER", "litellm")
    monkeypatch.setenv("LITELLM_MODEL", "gpt-4o")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")  # no proxy key/base
    llm = get_llm()
    assert llm is not None
    llm.complete([{"role": "user", "content": "hi"}])
    # no api_base => provider auto-routing, no forced proxy provider
    assert "custom_llm_provider" not in calls["kwargs"]


def test_litellm_unconfigured_returns_none(monkeypatch):
    monkeypatch.setenv("DQT_LLM_PROVIDER", "litellm")
    monkeypatch.setenv("LITELLM_MODEL", "gpt-4o")  # but no key/base/native
    assert get_llm() is None


def test_unknown_provider_raises(monkeypatch):
    monkeypatch.setenv("DQT_LLM_PROVIDER", "bogus")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    with pytest.raises(ValueError, match="Unknown DQT_LLM_PROVIDER"):
        get_llm()


def test_shared_knobs_parsed(monkeypatch):
    calls = _fake_litellm(monkeypatch)
    monkeypatch.setenv("DQT_LLM_PROVIDER", "litellm")
    monkeypatch.setenv("LITELLM_MODEL", "gpt-4o")
    monkeypatch.setenv("LITELLM_API_KEY", "k")
    monkeypatch.setenv("DQT_LLM_MAX_TOKENS", "321")
    monkeypatch.setenv("DQT_LLM_TEMPERATURE", "0.7")
    llm = get_llm()
    llm.complete([{"role": "user", "content": "hi"}])
    assert calls["kwargs"]["max_tokens"] == 321
    assert calls["kwargs"]["temperature"] == 0.7
