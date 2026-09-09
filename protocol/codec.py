from __future__ import annotations

import base64
import hashlib
import json
from typing import Any


def b64(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def unb64(value: str) -> bytes:
    return base64.b64decode(value.encode("ascii"), validate=True)


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def sha3(value: bytes) -> bytes:
    return hashlib.sha3_256(value).digest()
