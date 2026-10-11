from collections.abc import Callable
from dataclasses import dataclass, field
import json
import logging
import os
import time
from typing import Any, TextIO

HANDSHAKE_PROTOCOL_VERSIONS_NEWEST_FIRST = ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603
JSON_TYPE_CHECKS: dict[str, Callable[[Any], bool]] = {
    "string": lambda value: isinstance(value, str),
    "integer": lambda value: isinstance(value, int) and not isinstance(value, bool),
    "boolean": lambda value: isinstance(value, bool),
    "array": lambda value: isinstance(value, list),
    "null": lambda value: value is None,
}
logger = logging.getLogger(__name__)


class McpToolFailure(Exception):
    pass


class _InvalidParams(Exception):
    pass


@dataclass(frozen=True)
class McpTool:
    name: str
    description: str
    input_schema: dict[str, Any]
    run: Callable[[dict[str, Any]], dict[str, Any]]
    annotations: dict[str, bool] = field(default_factory=dict)

    def listing(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
            "annotations": self.annotations,
        }


class McpStdioServer:
    def __init__(self, name: str, version: str, instructions: str, tools: list[McpTool]):
        self.name = name
        self.version = version
        self.instructions = instructions
        self.tools_by_name = {tool.name: tool for tool in tools}
        self._answer_by_method: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
            "initialize": self._initialize,
            "ping": lambda params: {},
            "tools/list": lambda params: {"tools": [tool.listing() for tool in self.tools_by_name.values()]},
            "tools/call": self._call_tool,
        }

    def serve_stdio(self):
        incoming, outgoing = _claim_standard_streams_for_protocol()
        self.answer_messages(incoming, outgoing)

    def answer_messages(self, incoming: TextIO, outgoing: TextIO):
        for line in incoming:
            if not line.strip():
                continue
            reply = self._reply_to(line)
            if reply is not None:
                outgoing.write(json.dumps(reply, ensure_ascii=False, allow_nan=False) + "\n")
                outgoing.flush()

    def _reply_to(self, line: str) -> dict[str, Any] | None:
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            return _error_reply(None, PARSE_ERROR, "Parse error")
        if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
            return _error_reply(None, INVALID_REQUEST, "Expected a JSON-RPC 2.0 message")
        method, request_id = message.get("method"), message.get("id")
        if "id" not in message or not isinstance(method, str):
            return None
        answer = self._answer_by_method.get(method)
        if answer is None:
            return _error_reply(request_id, METHOD_NOT_FOUND, f"Method not found: {method}")
        params = message.get("params") or {}
        if not isinstance(params, dict):
            return _error_reply(request_id, INVALID_PARAMS, "params must be an object")
        try:
            return {"jsonrpc": "2.0", "id": request_id, "result": answer(params)}
        except _InvalidParams as exc:
            return _error_reply(request_id, INVALID_PARAMS, str(exc))
        except Exception as exc:
            # One bad request must not end the loop and disconnect the client.
            logger.exception("MCP method %s raised unexpectedly", method)
            return _error_reply(request_id, INTERNAL_ERROR, f"Internal error: {exc}")

    def _initialize(self, params: dict[str, Any]) -> dict[str, Any]:
        requested = params.get("protocolVersion")
        if requested in HANDSHAKE_PROTOCOL_VERSIONS_NEWEST_FIRST:
            version = requested
        else:
            version = HANDSHAKE_PROTOCOL_VERSIONS_NEWEST_FIRST[0]
        return {
            "protocolVersion": version,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": self.name, "version": self.version},
            "instructions": self.instructions,
        }

    def _call_tool(self, params: dict[str, Any]) -> dict[str, Any]:
        tool = self.tools_by_name.get(params.get("name", ""))
        if tool is None:
            raise _InvalidParams(f"Unknown tool: {params.get('name')}")
        arguments = params.get("arguments") or {}
        if violation := _argument_violation(tool.input_schema, arguments):
            return _failed_tool_result(violation)
        started = time.monotonic()
        try:
            data = tool.run(arguments)
        except McpToolFailure as exc:
            logger.warning("MCP tool %s failed in %.2fs: %s", tool.name, time.monotonic() - started, exc)
            return _failed_tool_result(str(exc))
        except Exception as exc:
            logger.exception("MCP tool %s raised unexpectedly", tool.name)
            return _failed_tool_result(f"runtime_error: {exc}")
        logger.info("MCP tool %s succeeded in %.2fs", tool.name, time.monotonic() - started)
        text = json.dumps(data, ensure_ascii=False, sort_keys=True, allow_nan=False)
        return {"content": [{"type": "text", "text": text}], "structuredContent": data, "isError": False}


def _claim_standard_streams_for_protocol() -> tuple[TextIO, TextIO]:
    # Libraries and child processes must not read the client's messages or write into the protocol stream.
    incoming = os.fdopen(os.dup(0), "r", encoding="utf-8", errors="replace")
    outgoing = os.fdopen(os.dup(1), "w", encoding="utf-8")
    null_input = os.open(os.devnull, os.O_RDONLY)
    os.dup2(null_input, 0)
    os.close(null_input)
    os.dup2(2, 1)
    return incoming, outgoing


def _argument_violation(schema: dict[str, Any], arguments: Any) -> str | None:
    if not isinstance(arguments, dict):
        return "Arguments must be an object"
    properties = schema.get("properties", {})
    for name in schema.get("required", []):
        if name not in arguments:
            return f"Missing required argument: {name}"
    for name, value in arguments.items():
        if name not in properties:
            return f"Unknown argument: {name}"
        if violation := _value_violation(properties[name], value):
            return f"{name} {violation}"
    return None


def _value_violation(schema: dict[str, Any], value: Any) -> str | None:
    allowed_types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
    if not any(JSON_TYPE_CHECKS[allowed](value) for allowed in allowed_types):
        return f"must be {' or '.join(allowed_types)}"
    if JSON_TYPE_CHECKS["integer"](value):
        if "minimum" in schema and value < schema["minimum"]:
            return f"must be at least {schema['minimum']}"
        if "maximum" in schema and value > schema["maximum"]:
            return f"must be at most {schema['maximum']}"
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            return f"must have at least {schema['minItems']} item(s)"
        for item in value:
            if violation := _value_violation(schema["items"], item):
                return f"items {violation}"
    return None


def _failed_tool_result(message: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": message}], "isError": True}


def _error_reply(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}
