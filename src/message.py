import json
from typing import Any

def pack(op: str, **kwargs: Any) -> bytes:
    payload = {"op": op, **kwargs}
    return json.dumps(payload).encode()

def unpack(data: bytes) -> dict[str, Any]:
    return json.loads(data.decode())

