
import asyncio
import json
import logging

from fastapi import Request
from fastapi.responses import JSONResponse

from app.main import app


def test_unexpected_exception_returns_generic_500_response(caplog):
    handler = app.exception_handlers[Exception]

    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/test-error",
            "headers": [],
            "query_string": b"",
            "server": ("testserver", 80),
            "scheme": "http",
            "client": ("testclient", 123),
            "root_path": "",
        }
    )

    exception = RuntimeError("Internal database details")

    with caplog.at_level(logging.ERROR, logger="app.main"):
        response = asyncio.run(handler(request, exception))

    assert isinstance(response, JSONResponse)
    assert response.status_code == 500
    assert json.loads(response.body) == {
        "detail": "Internal server error"
    }

    assert "Internal database details" not in response.body.decode()
    assert "Unhandled exception" in caplog.text
    assert "Internal database details" in caplog.text
