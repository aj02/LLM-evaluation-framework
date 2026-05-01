"""Target adapters: anything that turns an input into an output."""
from __future__ import annotations

import asyncio
import shlex
import subprocess
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import httpx
import jmespath
import yaml
from jinja2 import Template
from pydantic import BaseModel, ConfigDict, Field


class TargetError(RuntimeError):
    """Raised when a target call fails in a way the runner should record."""


class Target(ABC):
    """Abstract target: input dict -> output (any JSON-able value)."""

    name: str = "target"

    @abstractmethod
    async def call(self, input_value: Any) -> Any:
        """Run the target on a single input."""

    def summary(self) -> dict[str, Any]:
        """Stable, JSON-able snapshot recorded with each run."""
        return {"type": type(self).__name__, "name": self.name}


class CallableTarget(Target):
    """Wraps a sync or async Python callable."""

    def __init__(
        self,
        fn: Callable[[Any], Any] | Callable[[Any], Awaitable[Any]],
        name: str = "callable",
    ) -> None:
        self.fn = fn
        self.name = name

    async def call(self, input_value: Any) -> Any:
        result = self.fn(input_value)
        if asyncio.iscoroutine(result):
            return await result
        return result

    def summary(self) -> dict[str, Any]:
        return {
            "type": "CallableTarget",
            "name": self.name,
            "fn": getattr(self.fn, "__qualname__", repr(self.fn)),
        }


class HTTPTargetConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str
    method: str = "POST"
    headers: dict[str, str] = Field(default_factory=dict)
    payload_template: str | None = None
    response_path: str | None = None
    timeout_s: float = 30.0
    name: str = "http"


class HTTPTarget(Target):
    """HTTP endpoint target.

    payload_template: a Jinja template string (variable: ``input``). If the
        rendered template parses as JSON, it is sent as JSON; otherwise raw.
    response_path: a JMESPath expression used to extract the output from the
        JSON response. If unset, the raw decoded body is returned.
    """

    def __init__(self, config: HTTPTargetConfig) -> None:
        self.config = config
        self.name = config.name
        self._template: Template | None = (
            Template(config.payload_template) if config.payload_template else None
        )
        self._client: httpx.AsyncClient | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HTTPTarget:
        return cls(HTTPTargetConfig.model_validate(data))

    async def _client_lazy(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.config.timeout_s)
        return self._client

    def _build_payload(self, input_value: Any) -> tuple[Any, dict[str, Any] | None]:
        if self._template is None:
            return None, input_value if isinstance(input_value, dict) else {"input": input_value}
        rendered = self._template.render(input=input_value)
        try:
            import json
            return json.loads(rendered), None
        except Exception:
            return rendered, None

    def _extract(self, data: Any) -> Any:
        if self.config.response_path is None:
            return data
        try:
            return jmespath.search(self.config.response_path, data)
        except Exception as e:
            raise TargetError(
                f"response_path {self.config.response_path!r} failed: {e}"
            ) from e

    async def call(self, input_value: Any) -> Any:
        client = await self._client_lazy()
        body, json_body = self._build_payload(input_value)
        try:
            if self.config.method.upper() == "GET":
                resp = await client.get(
                    self.config.url, headers=self.config.headers, params=json_body
                )
            elif json_body is not None:
                resp = await client.request(
                    self.config.method, self.config.url, headers=self.config.headers, json=json_body
                )
            elif isinstance(body, (dict, list)):
                resp = await client.request(
                    self.config.method, self.config.url, headers=self.config.headers, json=body
                )
            else:
                resp = await client.request(
                    self.config.method, self.config.url, headers=self.config.headers, content=body
                )
        except httpx.HTTPError as e:
            raise TargetError(f"HTTP request failed: {e}") from e

        if resp.status_code >= 400:
            raise TargetError(f"HTTP {resp.status_code}: {resp.text[:500]}")

        try:
            data = resp.json()
        except ValueError:
            data = resp.text
        return self._extract(data)

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def summary(self) -> dict[str, Any]:
        return {
            "type": "HTTPTarget",
            "name": self.name,
            "url": self.config.url,
            "method": self.config.method,
            "response_path": self.config.response_path,
        }


class ShellTargetConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    command_template: str
    timeout_s: float = 60.0
    name: str = "shell"
    parse_json: bool = False


class ShellTarget(Target):
    """Subprocess target. command_template is a Jinja template; ``input`` is
    available as a variable. stdout is captured and returned (optionally
    JSON-parsed)."""

    def __init__(self, config: ShellTargetConfig) -> None:
        self.config = config
        self.name = config.name
        self._template = Template(config.command_template)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ShellTarget:
        return cls(ShellTargetConfig.model_validate(data))

    async def call(self, input_value: Any) -> Any:
        cmd = self._template.render(input=input_value)
        # POSIX shlex correctly handles quoted args; on Windows users should
        # use forward slashes or escaped backslashes in the template (the same
        # rule POSIX shells apply).
        try:
            argv = shlex.split(cmd, posix=True)
        except ValueError as e:
            raise TargetError(f"command parse error: {e}") from e
        try:
            proc = subprocess.run(  # noqa: S603 — caller-supplied template
                argv,
                capture_output=True,
                text=True,
                timeout=self.config.timeout_s,
                check=False,
            )
        except subprocess.TimeoutExpired as e:
            raise TargetError(f"shell timeout after {self.config.timeout_s}s") from e
        except OSError as e:
            raise TargetError(f"shell launch failed: {e}") from e
        if proc.returncode != 0:
            raise TargetError(
                f"shell exit {proc.returncode}: {proc.stderr.strip()[:500] or proc.stdout[:500]}"
            )
        out = proc.stdout
        if self.config.parse_json:
            import json
            try:
                return json.loads(out)
            except json.JSONDecodeError as e:
                raise TargetError(f"shell stdout was not JSON: {e}") from e
        return out

    def summary(self) -> dict[str, Any]:
        return {
            "type": "ShellTarget",
            "name": self.name,
            "command_template": self.config.command_template,
        }


def load_target_config(path: str | Path) -> Target:
    """Load a target from a YAML or JSON file.

    File schema::

        type: http | callable | shell
        name: my-target
        # ...type-specific fields
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"target config not found: {p}")
    text = p.read_text(encoding="utf-8")
    if p.suffix.lower() in (".yaml", ".yml"):
        data = yaml.safe_load(text)
    else:
        import json
        data = json.loads(text)

    if not isinstance(data, dict) or "type" not in data:
        raise ValueError(f"{p}: target config must be an object with a 'type' field")

    kind = data.pop("type")
    if kind == "http":
        return HTTPTarget(HTTPTargetConfig.model_validate(data))
    if kind == "shell":
        return ShellTarget(ShellTargetConfig.model_validate(data))
    if kind == "callable":
        raise ValueError(
            "CallableTarget cannot be loaded from config — construct it in Python."
        )
    raise ValueError(f"unknown target type: {kind!r}")
