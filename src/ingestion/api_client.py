# src/ingestion/api_client.py
from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

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

    logger.info(
        "Starting fetch_all endpoint=%s page_size=%s max_retries=%s base_url=%s",
        endpoint,
        page_size,
        max_retries,
        API_BASE_URL,
    )

    while True:
        paged_params = dict(params)
        paged_params.update({"limit": page_size, "offset": offset})

        url = f"{API_BASE_URL}{endpoint}"

        payload: Optional[Dict[str, Any]] = None
        last_error: Optional[Exception] = None

        for attempt in range(1, max_retries + 1):
            try:
                logger.debug("GET %s params=%s (attempt %d/%d)", url, paged_params, attempt, max_retries)

                response = requests.get(url, params=paged_params, timeout=timeout_seconds)
                response.raise_for_status()

                json_body = response.json()
                if not isinstance(json_body, dict):
                    raise ValueError(f"Expected JSON object but received {type(json_body)}")

                payload = json_body
                break

            except requests.HTTPError as exc:
                # Use exc.response (safe) instead of relying on a local 'response'
                response_obj = getattr(exc, "response", None)
                status_code = getattr(response_obj, "status_code", None)

                body = ""
                if response_obj is not None:
                    text = getattr(response_obj, "text", "")
                    if isinstance(text, str):
                        body = text

                last_error = exc
                logger.exception(
                    "HTTP error fetching %s (attempt %d/%d). status=%s body=%s",
                    url,
                    attempt,
                    max_retries,
                    status_code if status_code is not None else "n/a",
                    body[:1000],
                )

                if attempt >= max_retries:
                    raise RuntimeError(
                        f"Failed GET {url} (status={status_code if status_code is not None else 'n/a'}). "
                        f"Response body: {body[:1000]}"
                    ) from exc

                time.sleep(1.5 * attempt)

            except (requests.RequestException, ValueError, KeyError) as exc:
                # Network issues, JSON decode issues, or validation issues
                last_error = exc
                logger.exception(
                    "Request/parse error fetching %s (attempt %d/%d): %s",
                    url,
                    attempt,
                    max_retries,
                    exc,
                )

                if attempt >= max_retries:
                    raise RuntimeError(f"Failed GET {url} after {max_retries} retries: {exc}") from exc

                time.sleep(1.5 * attempt)

        if payload is None:
            raise RuntimeError(f"No payload returned from {url}. Last error: {last_error}")

        rows = payload.get("data")
        if rows is None:
            raise KeyError(
                f"Response from {url} does not contain 'data'. Keys found: {list(payload.keys())}"
            )
        if not isinstance(rows, list):
            raise ValueError(f"'data' must be a list, got {type(rows)}")

        all_rows.extend(rows)

        returned = payload.get("returned_records", len(rows))
        total = payload.get("total_records")

        logger.info(
            "Fetched page endpoint=%s offset=%d returned=%s total=%s accumulated=%d",
            endpoint,
            offset,
            returned,
            total,
            len(all_rows),
        )

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

    logger.info("Completed fetch_all endpoint=%s total_rows=%d", endpoint, len(all_rows))
    return all_rows


# Convenience wrappers
def fetch_devices(limit: int = 500) -> List[Dict[str, Any]]:
    return fetch_all("/devices", page_size=limit)


def fetch_incidents(limit: int = 500) -> List[Dict[str, Any]]:
    return fetch_all("/incidents", page_size=limit)


def fetch_lifecycle_events(limit: int = 500) -> List[Dict[str, Any]]:
    return fetch_all("/lifecycle-events", page_size=limit)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
    print("Testing API client...")

    devices = fetch_devices()
    incidents = fetch_incidents()
    lifecycle = fetch_lifecycle_events()

    print(f"Devices: {len(devices):,}")
    print(f"Incidents: {len(incidents):,}")
    print(f"Lifecycle events: {len(lifecycle):,}")