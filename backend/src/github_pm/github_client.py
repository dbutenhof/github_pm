"""Bounded, observable GitHub transport with scoped conditional REST caching.

Generated-by: Codex
"""

from collections import OrderedDict
from contextlib import contextmanager
from copy import deepcopy
from hashlib import sha256
import re
from threading import Lock
import time
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests

from github_pm.context import context
from github_pm.logger import logger

_TIMEOUT = (5, 45)
_MAX_ATTEMPTS = 5
_CACHE_LIMIT = 256
_OPERATION_TIMEOUT = 300
_cache = OrderedDict()
_state_lock = Lock()
_gates = {}


class _Gate:
    def __init__(self):
        self.lock = Lock()
        self.write_at = 0.0
        self.resume_at = 0.0
        self.revision = 0


def _page_url(url):
    parts = urlsplit(url)
    params = dict(parse_qsl(parts.query, keep_blank_values=True))
    params.setdefault("per_page", "100")
    return urlunsplit(parts._replace(query=urlencode(params)))


class Connector:
    def __init__(self, github_token: str, *, github_repo: str | None = None):
        self.github_token = github_token
        self.base_url = "https://api.github.com"
        self.owner, self.repo = (github_repo or context.github_repo).split("/", 1)
        self.scope = (sha256(github_token.encode()).hexdigest(), self.owner, self.repo)
        with _state_lock:
            self.gate = _gates.setdefault(self.scope[0], _Gate())
        self.github = requests.session()
        self.github.headers.update(
            {
                "Authorization": f"Bearer {github_token}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "Project-Manager",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )
        self.metrics = dict(
            calls=0, bytes=0, retries=0, elapsed=0.0, graphql_cost=0, not_modified=0
        )
        self.response = None
        self.closed = False
        self.deadline = time.monotonic() + _OPERATION_TIMEOUT

    def close(self):
        if not self.closed:
            self.closed = True
            self.github.close()
            logger.info(
                "GitHub operation %s/%s: %s", self.owner, self.repo, self.metrics
            )

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _invalidate(self):
        with _state_lock:
            self.gate.revision += 1
            for key in list(_cache):
                if key[0] == self.scope:
                    del _cache[key]

    def _remaining(self):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("GitHub operation exceeded its five-minute deadline")
        return remaining

    def _sleep(self, delay):
        if delay > self._remaining():
            raise TimeoutError("GitHub retry would exceed the operation deadline")
        time.sleep(delay)

    @contextmanager
    def _reserved(self):
        if not self.gate.lock.acquire(timeout=self._remaining()):
            raise TimeoutError("Timed out waiting for the GitHub request queue")
        try:
            yield
        finally:
            self.gate.lock.release()

    def _request(self, method, url, *, read=False, **kwargs):
        started = time.monotonic()
        try:
            with self._reserved():
                for attempt in range(_MAX_ATTEMPTS):
                    wait = self.gate.resume_at - time.time()
                    if wait > 60:
                        raise RuntimeError(
                            "GitHub rate limit active; retry after its reset time"
                        )
                    if wait > 0:
                        self._sleep(wait)
                    if not read:
                        pause = 1.0 - (time.monotonic() - self.gate.write_at)
                        if pause > 0:
                            self._sleep(pause)
                        self.gate.write_at = time.monotonic()
                        # A failed/ambiguous write may still have changed GitHub.
                        self._invalidate()
                    remaining_time = self._remaining()
                    timeout = tuple(
                        min(value, remaining_time / 2) for value in _TIMEOUT
                    )
                    response = getattr(self.github, method)(
                        url, timeout=timeout, **kwargs
                    )
                    self.metrics["calls"] += 1
                    content = response.content
                    if isinstance(content, (bytes, str)):
                        self.metrics["bytes"] += len(content)
                    headers = (
                        response.headers
                        if isinstance(response.headers, dict)
                        else dict(response.headers)
                    )
                    retry_after = headers.get("Retry-After") or headers.get(
                        "retry-after"
                    )
                    remaining = headers.get("X-RateLimit-Remaining") or headers.get(
                        "x-ratelimit-remaining"
                    )
                    for name in ("Limit", "Remaining", "Reset", "Resource"):
                        value = response.headers.get(f"X-RateLimit-{name}")
                        if isinstance(value, str):
                            self.metrics["rate_" + name.lower()] = value
                    graphql_throttled = False
                    if (
                        read
                        and method == "post"
                        and url.endswith("/graphql")
                        and response.status_code == 200
                    ):
                        result = response.json()
                        graphql_throttled = any(
                            error.get("type") == "RATE_LIMITED"
                            for error in result.get("errors", [])
                        )
                    throttled = (
                        graphql_throttled
                        or response.status_code == 429
                        or (
                            response.status_code == 403
                            and (
                                retry_after
                                or remaining == "0"
                                or "rate limit" in str(response.text).lower()
                            )
                        )
                    )
                    if throttled:
                        reset = headers.get("X-RateLimit-Reset") or headers.get(
                            "x-ratelimit-reset"
                        )
                        delay = (
                            float(retry_after)
                            if retry_after
                            else (
                                max(0, float(reset) - time.time())
                                if remaining == "0" and reset
                                else 60 * (attempt + 1)
                            )
                        )
                        self.gate.resume_at = time.time() + delay
                    else:
                        delay = 1.5 * (attempt + 1)
                    if (
                        read
                        and (throttled or response.status_code in (502, 503, 504))
                        and attempt < _MAX_ATTEMPTS - 1
                        and delay <= 60
                    ):
                        self.metrics["retries"] += 1
                        self._sleep(delay)
                        continue
                    response.raise_for_status()
                    self.response = response
                    return response
        finally:
            self.metrics["elapsed"] += time.monotonic() - started

    def _get_response(self, url, headers=None):
        cacheable = bool(re.search(r"/(milestones|labels|assignees)(?:\?|$)", url))
        key = (self.scope, url, tuple(sorted((headers or {}).items())))
        with _state_lock:
            cached = _cache.get(key) if cacheable else None
            revision = self.gate.revision
        request_headers = dict(headers or {})
        if cached:
            for name, value in cached[2].items():
                request_headers[name] = value
        response = self._request("get", url, headers=request_headers or None, read=True)
        if response.status_code == 304:
            if not cached:
                raise RuntimeError(
                    "GitHub returned 304 without a cached representation"
                )
            self.metrics["not_modified"] += 1
            return deepcopy(cached[0]), cached[1]
        data = response.json()
        links = response.headers.get("link") or response.headers.get("Link") or ""
        if not isinstance(links, str):
            links = ""
        validators = {}
        for source, target in [
            ("ETag", "If-None-Match"),
            ("Last-Modified", "If-Modified-Since"),
        ]:
            value = response.headers.get(source)
            if isinstance(value, str):
                validators[target] = value
        if cacheable and validators:
            with _state_lock:
                if revision != self.gate.revision:
                    return data, links
                _cache[key] = (deepcopy(data), links, validators)
                _cache.move_to_end(key)
                while len(_cache) > _CACHE_LIMIT:
                    _cache.popitem(last=False)
        return data, links

    def get(self, path, headers=None):
        return self._get_response(f"{self.base_url}{path}", headers)[0]

    def get_paged(self, path, headers=None):
        url = _page_url(f"{self.base_url}{path}")
        results, seen = [], set()
        while url:
            if url in seen or not url.startswith(self.base_url + "/"):
                raise RuntimeError("Invalid GitHub pagination link")
            seen.add(url)
            data, links = self._get_response(url, headers)
            if not isinstance(data, list):
                raise RuntimeError("Expected a GitHub list response")
            results.extend(data)
            url = next(
                (
                    link["url"]
                    for link in requests.utils.parse_header_links(links)
                    if link.get("rel") == "next"
                ),
                None,
            )
        return results

    def search_issue_items(self, search_query, headers=None):
        from github_pm.report_queries import rest_search

        return rest_search(lambda path: self.get(path, headers=headers), search_query)

    def post(self, path, data, headers=None):
        read = path == "/graphql" and bool(
            re.match(r"\s*(query\b|\{)", data.get("query", ""))
        )
        response = self._request(
            "post", f"{self.base_url}{path}", json=data, headers=headers, read=read
        )
        result = response.json() if response.content else {}
        if path == "/graphql" and isinstance(result, dict):
            rate = (result.get("data") or {}).get("rateLimit") or {}
            self.metrics["graphql_cost"] += rate.get("cost", 0)
        return result

    def patch(self, path, data, headers=None):
        response = self._request(
            "patch", f"{self.base_url}{path}", json=data, headers=headers
        )
        return response.json()

    def delete(self, path, data=None, headers=None):
        response = self._request(
            "delete", f"{self.base_url}{path}", json=data, headers=headers
        )
        return response.json() if response.content else {}

    def post_text(self, path, text, headers=None):
        response = self._request(
            "post",
            f"{self.base_url}{path}",
            data=text.encode("utf-8"),
            headers={"Content-Type": "text/plain; charset=utf-8", **(headers or {})},
            read=True,
        )
        return response.text
