# tests/test_api_client.py
import requests
import pytest
from unittest.mock import Mock, patch

from src.ingestion import api_client


def make_response(status_code=200, json_body=None, text_body="", raise_for_status_exc=None):
    resp = Mock(spec=requests.Response)
    resp.status_code = status_code
    resp.text = text_body
    if json_body is None:
        json_ret = {}
    else:
        json_ret = json_body

    resp.json = Mock(return_value=json_ret)

    def raise_for_status():
        if raise_for_status_exc:
            raise raise_for_status_exc

    resp.raise_for_status = Mock(side_effect=raise_for_status)
    return resp


@patch("src.ingestion.api_client.requests.get")
def test_fetch_all_success(mock_get):
    # Simulate two pages, then finished
    page1 = {"data": [{"id": 1}, {"id": 2}], "returned_records": 2, "total_records": 3}
    page2 = {"data": [{"id": 3}], "returned_records": 1, "total_records": 3}
    mock_get.side_effect = [make_response(json_body=page1), make_response(json_body=page2)]

    rows = api_client.fetch_all("/anything", page_size=2)
    assert isinstance(rows, list)
    assert len(rows) == 3
    assert rows[-1]["id"] == 3


@patch("src.ingestion.api_client.requests.get")
def test_fetch_all_server_error_includes_body(mock_get):
    # Simulate a 500 response with HTML body; ensure the raised RuntimeError includes the body snippet.
    http_exc = requests.HTTPError("500 Server Error")
    resp = make_response(status_code=500, text_body="<html>internal error stacktrace</html>", raise_for_status_exc=http_exc)
    mock_get.return_value = resp

    with pytest.raises(RuntimeError) as excinfo:
        api_client.fetch_all("/broken", page_size=1, max_retries=1)

    msg = str(excinfo.value)
    assert "Failed GET" in msg
    assert "internal error" in msg.lower() or "internal" in msg.lower()