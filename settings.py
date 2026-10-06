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

# Questions allowed per browser session (0 = unlimited). Set this on public
# deployments so visitors cannot exhaust the API quota.
MAX_QUESTIONS_PER_SESSION = int(_secret("MAX_QUESTIONS_PER_SESSION", 0) or 0)

# Local LM Studio secrets
USE_LM_STUDIO = _bool_secret("USE_LM_STUDIO", False)
LM_STUDIO_API_KEY = _secret("LM_STUDIO_API_KEY", "") or ""
LM_STUDIO_API_BASE = _secret("LM_STUDIO_API_BASE", "") or ""
LM_STUDIO_CHAT_MODEL = _secret("LM_STUDIO_CHAT_MODEL", "") or ""
LM_STUDIO_EMBEDDING_MODEL = _secret("LM_STUDIO_EMBEDDING_MODEL", "") or ""

# Path to the dynamic events dataset used by the pressing time-series and
# pressing pitch features. Defaults to the legacy in-repo location; override
# via secrets.toml or env when the dataset lives elsewhere.
PRESSING_DATASET_PATH = _secret("PRESSING_DATASET_PATH", "dataset/dynamic_events_pl_24")
