from __future__ import annotations

from typing import Any


def clean_mojibake(value: Any) -> Any:
    """
    Normalize common mojibake / unicode punctuation to plain ASCII.

    This repo is frequently viewed/edited in environments that may decode UTF-8
    as Windows-1252, which can turn an em-dash into the visible sequence
    "\\u00e2\\u20ac\\u201d" (mojibake).
    """
    if not isinstance(value, str):
        return value

    # Dashes (UTF-8 -> cp1252 mojibake, plus the intended unicode chars).
    value = value.replace("\u00e2\u20ac\u201d", "-").replace("\u00e2\u20ac\u201c", "-")
    value = value.replace("\u2014", "-").replace("\u2013", "-")

    return value
