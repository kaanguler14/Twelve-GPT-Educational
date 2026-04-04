import os

import streamlit as st


def _secret(key: str, default=None):
    """Read Streamlit secrets when present; otherwise env vars; never require secrets.toml."""
    try:
        if key in st.secrets:
            return st.secrets[key]
    except FileNotFoundError:
            pass
    if key in os.environ:
        return os.environ[key]
    return default


def _bool_secret(key: str, default: bool = False) -> bool:
    raw = _secret(key, default)
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        return raw.strip().lower() in ("1", "true", "yes", "on")
    return bool(raw)


GPT_BASE = _secret("GPT_BASE")
GPT_VERSION = _secret("GPT_VERSION")
GPT_KEY = _secret("GPT_KEY")
GPT_CHAT_MODEL = _secret("GPT_CHAT_MODEL", "") or ""
GPT_EMBEDDINGS_MODEL = _secret("GPT_EMBEDDINGS_MODEL")


if "gpt-5-mini" in GPT_CHAT_MODEL:
    GPT_SUPPORTS_REASONING = True
    GPT_AVAILABLE_REASONING_EFFORTS = ["minimal", "low", "medium", "high"]
    GPT_SUPPORTS_TEMPERATURE = False
elif "gpt-5-nano" in GPT_CHAT_MODEL:
    GPT_SUPPORTS_REASONING = True
    GPT_AVAILABLE_REASONING_EFFORTS = ["minimal", "low", "medium", "high"]
    GPT_SUPPORTS_TEMPERATURE = False
elif "gpt-4o-mini" in GPT_CHAT_MODEL:
    GPT_SUPPORTS_REASONING = False
    GPT_AVAILABLE_REASONING_EFFORTS = []
    GPT_SUPPORTS_TEMPERATURE = True
else:
    GPT_SUPPORTS_REASONING = False
    GPT_AVAILABLE_REASONING_EFFORTS = []
    GPT_SUPPORTS_TEMPERATURE = True

# Gemini secrets
USE_GEMINI = _bool_secret("USE_GEMINI", False)
GEMINI_API_KEY = _secret("GEMINI_API_KEY", "") or ""
GEMINI_CHAT_MODEL = _secret("GEMINI_CHAT_MODEL", "") or ""
GEMINI_EMBEDDING_MODEL = _secret("GEMINI_EMBEDDING_MODEL", "") or ""
