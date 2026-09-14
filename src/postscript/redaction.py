"""Redact anything that should never sit in a receipt."""

from __future__ import annotations

import re
from typing import Any

DROP_KEYS = {"ssn", "pin", "password", "token", "approval_token", "secret"}
ACCOUNT_RE = re.compile(r"\b(\d{8,17})\b")
SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: ("[dropped]" if k.lower() in DROP_KEYS else redact(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, str):
        value = SSN_RE.sub("[ssn]", value)
        return ACCOUNT_RE.sub(lambda m: "*" * (len(m.group(1)) - 4) + m.group(1)[-4:], value)
    return value
