from __future__ import annotations

import sys

import pytest

from evalkit.core.target import ShellTarget, ShellTargetConfig, TargetError


# On Windows, POSIX shlex treats backslashes as escape characters.
# Use forward slashes for cross-platform tests.
PY = sys.executable.replace("\\", "/")


@pytest.mark.asyncio
async def test_shell_basic_stdout() -> None:
    config = ShellTargetConfig(
        command_template=PY + ' -c "print({{ input.n }} * 2, end=\'\')"',
        name="multiplier",
    )
    target = ShellTarget(config)
    out = await target.call({"n": 21})
    assert out == "42"


@pytest.mark.asyncio
async def test_shell_parse_json() -> None:
    config = ShellTargetConfig(
        command_template=PY + ' -c "import json; print(json.dumps({\'k\': {{ input.v }}}))"',
        parse_json=True,
    )
    target = ShellTarget(config)
    out = await target.call({"v": 7})
    assert out == {"k": 7}


@pytest.mark.asyncio
async def test_shell_nonzero_exit_becomes_target_error() -> None:
    config = ShellTargetConfig(
        command_template=PY + ' -c "import sys; sys.exit(2)"',
    )
    target = ShellTarget(config)
    with pytest.raises(TargetError, match="exit 2"):
        await target.call({})
