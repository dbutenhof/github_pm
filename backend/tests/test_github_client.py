"""Transport lifecycle, safe retries, scoped validators and responsiveness.

Generated-by: Codex
"""

import asyncio
import json
from threading import Event
from unittest.mock import Mock

from fastapi import FastAPI
import httpx
import pytest
import requests

from github_pm import github_client as gc
from github_pm.execution import offload


def response(status=200, data=None, headers=None):
    result = requests.Response()
    result.status_code = status
    result._content = json.dumps(data if data is not None else []).encode()
    result.headers.update(headers or {})
    result.url = "https://api.github.com/test"
    return result


@pytest.fixture
def session(monkeypatch):
    gc._cache.clear()
    gc._gates.clear()
    session = Mock()
    monkeypatch.setattr(gc.requests, "session", lambda: session)
    return session


def test_sessions_close_on_error_and_requests_have_timeouts(session):
    session.get.side_effect = requests.Timeout("timeout")
    with pytest.raises(requests.Timeout):
        with gc.Connector("token", github_repo="a/b") as client:
            client.get("/test")
    session.close.assert_called_once()
    assert session.get.call_args.kwargs["timeout"] == (5, 45)
    assert session.get.call_count == 1


def test_read_retry_but_no_ambiguous_write_replay(session, monkeypatch):
    sleep = Mock()
    monkeypatch.setattr(gc.time, "sleep", sleep)
    session.get.side_effect = [response(504), response(data={"ok": True})]
    with gc.Connector("token", github_repo="a/b") as client:
        assert client.get("/test") == {"ok": True}
        assert client.metrics["retries"] == 1
        assert client.metrics["calls"] == 2
        assert client.metrics["bytes"] > 0
        session.post.return_value = response(504)
        with pytest.raises(requests.HTTPError):
            client.post("/repos/a/b/issues/1/comments", {"body": "once"})
        assert session.post.call_count == 1
        session.post.side_effect = requests.Timeout("ambiguous")
        with pytest.raises(requests.Timeout):
            client.post("/repos/a/b/issues", {"title": "once"})
        assert session.post.call_count == 2


def test_conditional_cache_retains_paginated_representation_and_invalidates_on_write(
    session,
):
    link = '<https://api.github.com/repos/a/b/labels?per_page=100&page=2>; rel="next"'
    session.get.side_effect = [
        response(data=[{"name": "a"}], headers={"ETag": "one", "Link": link}),
        response(data=[{"name": "b"}], headers={"ETag": "two"}),
        response(304),
        response(304),
        response(data=[]),
    ]
    session.post.return_value = response(data={"name": "c"})
    with gc.Connector("token", github_repo="a/b") as client:
        assert client.get_paged("/repos/a/b/labels") == [{"name": "a"}, {"name": "b"}]
        assert client.get_paged("/repos/a/b/labels") == [{"name": "a"}, {"name": "b"}]
        assert session.get.call_args_list[2].kwargs["headers"] == {
            "If-None-Match": "one"
        }
        assert session.get.call_args_list[3].kwargs["headers"] == {
            "If-None-Match": "two"
        }
        assert client.metrics["not_modified"] == 2
        client.post("/repos/a/b/labels", {"name": "c"})
        client.get_paged("/repos/a/b/labels")
        assert session.get.call_args.kwargs["headers"] is None
        assert session.get.call_args_list[0].args[0].endswith("?per_page=100")


def test_cache_is_scoped_by_repository_and_authorization(session):
    session.get.return_value = response(data=[], headers={"ETag": "private"})
    for token, repo in [("a", "x/y"), ("b", "x/y"), ("a", "x/z")]:
        with gc.Connector(token, github_repo=repo) as client:
            client.get("/repos/x/y/labels")
            assert session.get.call_args.kwargs["headers"] is None
    with gc.Connector("a", github_repo="x/y") as client:
        client.get("/repos/x/y/labels")
        assert session.get.call_args.kwargs["headers"]["If-None-Match"] == "private"


def test_get_started_before_write_cannot_repopulate_cache(session):
    with gc.Connector("token", github_repo="a/b") as client:

        def read(*args, **kwargs):
            # Simulate a concurrent write after HTTP completion, before cache storage.
            client._invalidate()
            return response(data=["old"], headers={"ETag": "old"})

        session.get.side_effect = read
        client.get("/repos/a/b/labels")
        assert not gc._cache


def test_rate_limits_share_pause_and_report_headers(session, monkeypatch):
    wall = [1000.0]
    sleeps = []
    monkeypatch.setattr(gc.time, "time", lambda: wall[0])

    def sleep(seconds):
        sleeps.append(seconds)
        wall[0] += seconds

    monkeypatch.setattr(gc.time, "sleep", sleep)
    session.get.side_effect = [
        response(429, headers={"Retry-After": "2"}),
        response(data=[], headers={"X-RateLimit-Remaining": "4999"}),
    ]
    with gc.Connector("token", github_repo="a/b") as client:
        client.get("/test")
        assert sleeps == [2]
        assert client.metrics["retries"] == 1
        assert client.metrics["rate_remaining"] == "4999"
        assert client.gate is gc.Connector("token", github_repo="a/c").gate


def test_graphql_read_rate_limit_retries_and_records_cost(session, monkeypatch):
    monkeypatch.setattr(gc.time, "sleep", Mock())
    monkeypatch.setattr(gc.time, "time", lambda: 1000.0)
    session.post.side_effect = [
        response(
            data={"errors": [{"type": "RATE_LIMITED"}]}, headers={"Retry-After": "0"}
        ),
        response(data={"data": {"rateLimit": {"cost": 7}}}),
    ]
    with gc.Connector("token", github_repo="a/b") as client:
        client.post("/graphql", {"query": "query { rateLimit { cost } }"})
        assert client.metrics["graphql_cost"] == 7
        assert client.metrics["retries"] == 1


def test_operation_deadline_prevents_more_network_calls(session, monkeypatch):
    with gc.Connector("token", github_repo="a/b") as client:
        client.deadline = 0
        with pytest.raises(TimeoutError, match="deadline"):
            client.get("/test")
    session.get.assert_not_called()


@pytest.mark.asyncio
async def test_blocking_route_does_not_block_another_request():
    entered, release = Event(), Event()
    app = FastAPI()

    @app.get("/slow")
    @offload
    def slow():
        entered.set()
        assert release.wait(5)
        return {"done": True}

    @app.get("/fast")
    async def fast():
        return {"ready": True}

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="http://test"
    ) as client:
        pending = asyncio.create_task(client.get("/slow"))
        try:
            for _ in range(200):
                if entered.is_set():
                    break
                await asyncio.sleep(0.005)
            assert entered.is_set()
            result = await asyncio.wait_for(client.get("/fast"), timeout=1)
            assert result.json() == {"ready": True}
            assert not pending.done()
        finally:
            release.set()
            await pending
