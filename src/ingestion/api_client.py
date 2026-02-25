import os
import time
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


def fetch_all(
    endpoint: str,
    params: Optional[Dict[str, Any]] = None,
    page_size: int = 500,
    sleep_seconds: float = 0.0,
    max_retries: int = 3,
    timeout_seconds: int = 30,
) -> List[Dict[str, Any]]:
    """
    Fetch all records from a paginated REST endpoint using limit/offset.

    Expected response format:
    {
        "data": [...],
        "returned_records": 500,
        "total_records": 12345
    }
    """

    if not endpoint.startswith("/"):
        endpoint = "/" + endpoint

    if params is None:
        params = {}

    all_rows: List[Dict[str, Any]] = []
    offset = 0

    while True:
        paged_params = dict(params)
        paged_params.update({"limit": page_size, "offset": offset})

        url = f"{API_BASE_URL}{endpoint}"

        payload: Optional[Dict[str, Any]] = None
        last_error: Optional[Exception] = None

        # Retry loop
        for attempt in range(1, max_retries + 1):
            try:
                response = requests.get(
                    url,
                    params=paged_params,
                    timeout=timeout_seconds,
                )
                response.raise_for_status()

                json_body = response.json()

                if not isinstance(json_body, dict):
                    raise ValueError(
                        f"Expected JSON object but received {type(json_body)}"
                    )

                payload = json_body
                break

            except Exception as exc:
                last_error = exc
                if attempt < max_retries:
                    time.sleep(1.5 * attempt)
                else:
                    raise RuntimeError(
                        f"Failed GET {url} after {max_retries} retries: {exc}"
                    ) from exc

        if payload is None:
            raise RuntimeError(
                f"No payload returned from {url}. Last error: {last_error}"
            )

        rows = payload.get("data")

        if rows is None:
            raise KeyError(
                f"Response from {url} does not contain 'data'. "
                f"Keys found: {list(payload.keys())}"
            )

        if not isinstance(rows, list):
            raise ValueError(f"'data' must be a list, got {type(rows)}")

        all_rows.extend(rows)

        returned = payload.get("returned_records", len(rows))
        total = payload.get("total_records")

        # Stop conditions
        if returned == 0:
            break

        if isinstance(total, int) and len(all_rows) >= total:
            break

        if total is None and len(rows) < page_size:
            break

        offset += page_size

        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

    return all_rows


# Convenience wrappers
def fetch_devices(limit: int = 500) -> List[Dict[str, Any]]:
    return fetch_all("/devices", page_size=limit)


def fetch_incidents(limit: int = 500) -> List[Dict[str, Any]]:
    return fetch_all("/incidents", page_size=limit)


def fetch_lifecycle_events(limit: int = 500) -> List[Dict[str, Any]]:
    return fetch_all("/lifecycle-events", page_size=limit)


if __name__ == "__main__":
    print("Testing API client...")

    devices = fetch_devices()
    incidents = fetch_incidents()
    lifecycle = fetch_lifecycle_events()

    print(f"Devices: {len(devices):,}")
    print(f"Incidents: {len(incidents):,}")
    print(f"Lifecycle events: {len(lifecycle):,}")
