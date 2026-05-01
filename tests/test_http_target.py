from __future__ import annotations

import json

import httpx
import pytest
import respx

from evalkit.core.target import HTTPTarget, HTTPTargetConfig, TargetError


@pytest.mark.asyncio
async def test_post_json_with_response_path() -> None:
    config = HTTPTargetConfig(
        url="https://api.example.com/echo",
        method="POST",
        headers={"x-test": "1"},
        payload_template='{"q": {{ input.q | tojson }}}',
        response_path="data.answer",
        name="echo",
    )
    target = HTTPTarget(config)

    with respx.mock(assert_all_called=True) as mock:
        route = mock.post("https://api.example.com/echo").mock(
            return_value=httpx.Response(200, json={"data": {"answer": "yes"}})
        )
        out = await target.call({"q": "is it ok?"})
        await target.aclose()

    assert out == "yes"
    assert route.called
    sent = json.loads(route.calls.last.request.content)
    assert sent == {"q": "is it ok?"}


@pytest.mark.asyncio
async def test_no_response_path_returns_full_body() -> None:
    config = HTTPTargetConfig(url="https://api.example.com/x", method="POST")
    target = HTTPTarget(config)
    with respx.mock() as mock:
        mock.post("https://api.example.com/x").mock(
            return_value=httpx.Response(200, json={"a": 1, "b": 2})
        )
        out = await target.call({"q": "anything"})
        await target.aclose()
    assert out == {"a": 1, "b": 2}


@pytest.mark.asyncio
async def test_http_error_becomes_target_error() -> None:
    config = HTTPTargetConfig(url="https://api.example.com/fail", method="POST")
    target = HTTPTarget(config)
    with respx.mock() as mock:
        mock.post("https://api.example.com/fail").mock(
            return_value=httpx.Response(500, text="boom")
        )
        with pytest.raises(TargetError, match="HTTP 500"):
            await target.call({})
        await target.aclose()


@pytest.mark.asyncio
async def test_jmespath_extraction() -> None:
    config = HTTPTargetConfig(
        url="https://api.example.com/list",
        method="POST",
        response_path="results[0].id",
    )
    target = HTTPTarget(config)
    with respx.mock() as mock:
        mock.post("https://api.example.com/list").mock(
            return_value=httpx.Response(200, json={"results": [{"id": "abc"}, {"id": "def"}]})
        )
        out = await target.call({})
        await target.aclose()
    assert out == "abc"


@pytest.mark.asyncio
async def test_get_passes_input_as_query_params() -> None:
    config = HTTPTargetConfig(url="https://api.example.com/q", method="GET")
    target = HTTPTarget(config)
    with respx.mock() as mock:
        mock.get("https://api.example.com/q").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )
        out = await target.call({"x": "1"})
        await target.aclose()
    assert out == {"ok": True}


def test_target_summary_excludes_secrets() -> None:
    config = HTTPTargetConfig(
        url="https://api.example.com/x",
        headers={"authorization": "Bearer secret"},
    )
    s = HTTPTarget(config).summary()
    # summary should NOT include headers
    assert "authorization" not in json.dumps(s).lower()
