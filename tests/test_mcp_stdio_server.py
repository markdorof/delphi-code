import io
import json
import unittest

from delphi_code.infrastructure.mcp_stdio_server import McpStdioServer, McpTool, McpToolFailure


def echo(arguments):
    if arguments.get("fail"):
        raise McpToolFailure("broken: on purpose")
    return {"echoed": arguments.get("words", [])}


ECHO = McpTool(
    "echo",
    "Echo words",
    {
        "type": "object",
        "properties": {
            "words": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            "times": {"type": "integer", "minimum": 1, "maximum": 3},
            "fail": {"type": "boolean"},
        },
        "required": ["words"],
    },
    echo,
    {"readOnlyHint": True},
)


UNSERIALIZABLE = McpTool("unserializable", "Return NaN", {"type": "object"}, lambda arguments: {"score": float("nan")})


def replies_to(*messages, tools=(ECHO,)):
    incoming = io.StringIO("".join((m if isinstance(m, str) else json.dumps(m)) + "\n" for m in messages))
    outgoing = io.StringIO()
    McpStdioServer("test", "1.0", "Use echo", list(tools)).answer_messages(incoming, outgoing)
    return [json.loads(line) for line in outgoing.getvalue().splitlines()]


def request(request_id, method, params=None):
    return {"jsonrpc": "2.0", "id": request_id, "method": method, **({"params": params} if params else {})}


def call(arguments):
    return request(1, "tools/call", {"name": "echo", "arguments": arguments})


class McpStdioProtocol(unittest.TestCase):
    def test_initialize_echoes_a_supported_version_and_offers_the_newest_otherwise(self):
        supported, unknown = replies_to(
            request(1, "initialize", {"protocolVersion": "2025-03-26", "capabilities": {}}),
            request(2, "initialize", {"protocolVersion": "1999-01-01", "capabilities": {}}),
        )
        self.assertEqual(supported["result"]["protocolVersion"], "2025-03-26")
        self.assertEqual(supported["result"]["capabilities"], {"tools": {}})
        self.assertEqual(supported["result"]["serverInfo"], {"name": "test", "version": "1.0"})
        self.assertEqual(supported["result"]["instructions"], "Use echo")
        self.assertEqual(unknown["result"]["protocolVersion"], "2025-11-25")

    def test_notifications_and_responses_get_no_reply(self):
        replies = replies_to(
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 7, "result": {}},
            request(1, "ping"),
        )
        self.assertEqual(replies, [{"jsonrpc": "2.0", "id": 1, "result": {}}])

    def test_unknown_methods_and_malformed_lines_get_json_rpc_errors(self):
        discover, garbage, unknown_tool = replies_to(
            request(1, "server/discover"),
            "{not json",
            request(2, "tools/call", {"name": "missing"}),
        )
        self.assertEqual(discover["error"]["code"], -32601)
        self.assertEqual(garbage["error"]["code"], -32700)
        self.assertEqual(unknown_tool["error"]["code"], -32602)

    def test_unexpected_errors_get_an_internal_error_and_the_server_keeps_answering(self):
        broken, ping = replies_to(
            request(1, "tools/call", {"name": "unserializable"}), request(2, "ping"), tools=[UNSERIALIZABLE]
        )
        self.assertEqual(broken["error"]["code"], -32603)
        self.assertEqual(ping, {"jsonrpc": "2.0", "id": 2, "result": {}})

    def test_lists_tools_with_schema_and_annotations(self):
        (listing,) = replies_to(request(1, "tools/list"))
        (tool,) = listing["result"]["tools"]
        self.assertEqual(tool["name"], "echo")
        self.assertEqual(tool["inputSchema"]["required"], ["words"])
        self.assertEqual(tool["annotations"], {"readOnlyHint": True})

    def test_successful_calls_return_text_and_structured_content(self):
        (reply,) = replies_to(call({"words": ["a", "b"]}))
        result = reply["result"]
        self.assertFalse(result["isError"])
        self.assertEqual(result["structuredContent"], {"echoed": ["a", "b"]})
        self.assertEqual(json.loads(result["content"][0]["text"]), {"echoed": ["a", "b"]})

    def test_invalid_arguments_and_failures_are_tool_errors_the_agent_can_read(self):
        replies = replies_to(
            call({}),
            call({"words": []}),
            call({"words": [1]}),
            call({"words": ["a"], "times": 9}),
            call({"words": ["a"], "times": True}),
            call({"words": ["a"], "colour": "red"}),
            call({"words": ["a"], "fail": True}),
        )
        self.assertTrue(all(reply["result"]["isError"] for reply in replies))
        self.assertEqual(
            [reply["result"]["content"][0]["text"] for reply in replies],
            [
                "Missing required argument: words",
                "words must have at least 1 item(s)",
                "words items must be string",
                "times must be at most 3",
                "times must be integer",
                "Unknown argument: colour",
                "broken: on purpose",
            ],
        )


if __name__ == "__main__":
    unittest.main()
