from __future__ import annotations

import math
from typing import Any


def sanitize_for_json(obj: Any) -> Any:
    """
    Recursively convert non-JSON-compliant floats (NaN/Inf/-Inf) to None.
    Works for nested dict/list structures.
    """
    if obj is None:
        return None

    if isinstance(obj, float):
        # NaN or Infinity are not valid JSON numbers
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj

    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}

    if isinstance(obj, list):
        return [sanitize_for_json(v) for v in obj]

    # leave ints, strings, bools, etc.
    return obj