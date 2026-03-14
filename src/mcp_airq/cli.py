"""CLI for running air-Q tool functions without an MCP client."""

from __future__ import annotations

import argparse
import asyncio
import inspect
import json
import re
import sys
from collections.abc import Sequence
from types import SimpleNamespace
from typing import Any, Literal, get_args, get_origin

import aiohttp

from mcp_airq.config import load_config
from mcp_airq.devices import DeviceManager
from mcp_airq.tools import dangerous, read, write

ToolFunction = Any
TOOL_MODULES = (read, write, dangerous)
ERROR_PREFIXES = (
    "Configuration error:",
    "Authentication failed.",
    "API access denied.",
    "Unexpected response from device:",
    "Network error:",
    "Request timed out.",
    "Specify at most one of",
    "Specify at least one of",
    "For static IP, provide all of:",
)
SAFE_YAML_KEY = re.compile(r"^[A-Za-z0-9_-]+$")


def _collect_tools() -> dict[str, ToolFunction]:
    """Collect tool functions in module definition order."""
    tools: dict[str, ToolFunction] = {}
    for module in TOOL_MODULES:
        for name, value in vars(module).items():
            if name.startswith("_"):
                continue
            if inspect.iscoroutinefunction(value) and value.__module__ == module.__name__:
                tools[name] = value
    return tools


TOOLS = _collect_tools()


def _command_name(tool_name: str) -> str:
    """Convert a tool function name to a CLI command name."""
    return tool_name.replace("_", "-")


def _unwrap_optional(annotation: Any) -> Any:
    """Unwrap ``T | None`` to ``T``."""
    args = get_args(annotation)
    if type(None) in args:
        non_none = [arg for arg in args if arg is not type(None)]
        if len(non_none) == 1:
            return non_none[0]
    return annotation


def _docstring(fn: ToolFunction) -> str:
    """Return a normalized docstring for a tool function."""
    return inspect.getdoc(fn) or "Run this command."


def _add_argument(parser: argparse.ArgumentParser, name: str, parameter: inspect.Parameter) -> None:
    """Add one CLI argument based on a tool function parameter."""
    annotation = parameter.annotation if parameter.annotation is not inspect._empty else str
    annotation = _unwrap_optional(annotation)
    option = f"--{name.replace('_', '-')}"
    kwargs: dict[str, Any] = {"dest": name}

    if annotation is bool:
        kwargs["action"] = argparse.BooleanOptionalAction
        if parameter.default is inspect._empty:
            kwargs["required"] = True
        else:
            kwargs["default"] = parameter.default
        parser.add_argument(option, **kwargs)
        return

    origin = get_origin(annotation)
    if origin is list:
        item_type = get_args(annotation)[0] if get_args(annotation) else str
        kwargs["nargs"] = "+"
        kwargs["type"] = item_type
    elif origin is Literal:
        choices = list(get_args(annotation))
        kwargs["choices"] = choices
        kwargs["type"] = type(choices[0]) if choices else str
    else:
        kwargs["type"] = annotation if isinstance(annotation, type) else str

    if parameter.default is inspect._empty:
        kwargs["required"] = True
    else:
        kwargs["default"] = parameter.default

    parser.add_argument(option, **kwargs)


def _add_output_arguments(parser: argparse.ArgumentParser) -> None:
    """Add shared output formatting flags."""
    output_group = parser.add_mutually_exclusive_group()
    output_group.add_argument(
        "--json",
        action="store_const",
        const="json",
        dest="output_mode",
        help="Serialize the command result as JSON.",
    )
    output_group.add_argument(
        "--yaml",
        action="store_const",
        const="yaml",
        dest="output_mode",
        help="Serialize the command result as YAML.",
    )
    parser.add_argument(
        "--compact-json",
        action="store_true",
        help="Serialize the command result as compact JSON.",
    )
    parser.set_defaults(output_mode="text", compact_json=False)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for all air-Q tool commands."""
    parser = argparse.ArgumentParser(
        prog="mcp-airq",
        description="Run air-Q commands directly from the terminal.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    for tool_name, tool_fn in TOOLS.items():
        doc = _docstring(tool_fn)
        summary = doc.splitlines()[0]
        command = _command_name(tool_name)
        subparser = subparsers.add_parser(
            command,
            aliases=[tool_name],
            help=summary,
            description=doc,
        )
        subparser.set_defaults(tool_name=tool_name)
        _add_output_arguments(subparser)
        for name, parameter in inspect.signature(tool_fn).parameters.items():
            if name == "ctx":
                continue
            _add_argument(subparser, name, parameter)

    return parser


def _build_context(manager: DeviceManager) -> Any:
    """Build the minimal context object expected by the tool functions."""
    return SimpleNamespace(
        request_context=SimpleNamespace(lifespan_context=manager),
    )


async def _invoke_tool(tool_name: str, arguments: dict[str, Any]) -> Any:
    """Invoke one tool function inside a short-lived client session."""
    try:
        configs = load_config()
    except ValueError as exc:
        return f"Configuration error: {exc}"

    timeout = aiohttp.ClientTimeout(total=30, connect=15)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        manager = DeviceManager(session, configs)
        ctx = _build_context(manager)
        return await TOOLS[tool_name](ctx, **arguments)


async def _run_command(args: argparse.Namespace) -> Any:
    """Run the parsed CLI command."""
    tool_name = args.tool_name
    params = {name: getattr(args, name) for name in inspect.signature(TOOLS[tool_name]).parameters if name != "ctx"}
    return await _invoke_tool(tool_name, params)


def _is_error_result(result: Any) -> bool:
    """Detect user-facing error strings returned by tool functions."""
    return isinstance(result, str) and result.startswith(ERROR_PREFIXES)


def _coerce_structured_data(result: Any) -> Any:
    """Parse JSON strings so they can be re-serialized for CLI output."""
    if isinstance(result, str):
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return result
    return result


def _yaml_key(value: str) -> str:
    """Render one YAML mapping key."""
    if SAFE_YAML_KEY.fullmatch(value):
        return value
    return json.dumps(value, ensure_ascii=False)


def _yaml_scalar(value: Any) -> str:
    """Render one YAML scalar."""
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(value, ensure_ascii=False)


def _to_yaml(value: Any, indent: int = 0) -> str:
    """Serialize JSON-compatible data to a simple YAML representation."""
    prefix = " " * indent
    if isinstance(value, dict):
        if not value:
            return "{}"
        lines: list[str] = []
        for key, item in value.items():
            rendered_key = _yaml_key(str(key))
            if isinstance(item, (dict, list)) and item:
                lines.append(f"{prefix}{rendered_key}:")
                lines.append(_to_yaml(item, indent + 2))
            elif isinstance(item, dict):
                lines.append(f"{prefix}{rendered_key}: {{}}")
            elif isinstance(item, list):
                lines.append(f"{prefix}{rendered_key}: []")
            else:
                lines.append(f"{prefix}{rendered_key}: {_yaml_scalar(item)}")
        return "\n".join(lines)

    if isinstance(value, list):
        if not value:
            return "[]"
        lines = []
        for item in value:
            if isinstance(item, (dict, list)) and item:
                lines.append(f"{prefix}-")
                lines.append(_to_yaml(item, indent + 2))
            elif isinstance(item, dict):
                lines.append(f"{prefix}- {{}}")
            elif isinstance(item, list):
                lines.append(f"{prefix}- []")
            else:
                lines.append(f"{prefix}- {_yaml_scalar(item)}")
        return "\n".join(lines)

    return f"{prefix}{_yaml_scalar(value)}"


def _emit_textual_result(args: argparse.Namespace, result: Any) -> None:
    """Emit one non-binary result according to the selected output mode."""
    if args.output_mode == "text" and not args.compact_json:
        print(result)
        return

    data = _coerce_structured_data(result)
    if args.output_mode == "yaml":
        print(_to_yaml(data))
        return

    if args.output_mode == "json" or args.compact_json:
        if args.compact_json:
            print(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
        else:
            print(json.dumps(data, ensure_ascii=False, indent=2))
        return

    print(result)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point for direct terminal usage."""
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    result = asyncio.run(_run_command(args))
    if _is_error_result(result):
        print(result, file=sys.stderr)
        return 1
    if result is not None:
        _emit_textual_result(args, result)
    return 0
