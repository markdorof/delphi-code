from ..text_layout import TextStyle, home_abbreviated

SUPPORTED_AGENTS_HINT = "Supported: Claude Desktop, Claude Code, Codex, Cursor, VS Code and Gemini CLI"
RESTART_HINT = "Restart running agents to apply the change."
OUTCOMES_THAT_CHANGE_AN_AGENT = {"added", "removed"}


class AgentConnectionsView:
    def __init__(self, connections: list[dict]):
        self._connections = connections

    def lines(self, style: TextStyle) -> list[str]:
        if not self._connections:
            return ["No supported agents found.", style.dim(SUPPORTED_AGENTS_HINT)]
        lines = [self._line(connection, style) for connection in self._connections]
        if any(connection["outcome"] in OUTCOMES_THAT_CHANGE_AN_AGENT for connection in self._connections):
            lines.append(style.dim(RESTART_HINT))
        return lines

    def _line(self, connection: dict, style: TextStyle) -> str:
        name = style.bold(connection["title"])
        config = home_abbreviated(connection["config"])
        detail = f" {connection['detail']}" if connection["detail"] else ""
        match connection["outcome"]:
            case "added":
                return f"{style.green('✓')} {name}: added to {config}"
            case "already_configured":
                return f"{style.green('✓')} {name}: already configured in {config}{style.dim(detail)}"
            case "removed":
                return f"{style.green('✓')} {name}: removed from {config}"
            case "not_configured":
                return f"{style.dim('-')} {name}: not configured"
            case "kept":
                return f"{style.dim('-')} {name}: left {config} alone,{detail}"
            case "not_found":
                return f"{style.dim('-')} {name}: not installed"
            case _:
                location = f"{config}: " if config else ""
                return f"{style.red('✗')} {name}: {location}{connection['detail']}"
