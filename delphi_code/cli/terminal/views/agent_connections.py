from ....domain.agent_connection import AgentConnection, Outcome
from ..text_layout import TextStyle, home_abbreviated

SUPPORTED_AGENTS_HINT = "Supported: Claude Desktop, Claude Code, Codex, Cursor, VS Code, Gemini CLI and OpenCode"
RESTART_HINT = "Restart running agents to apply the change."
OUTCOMES_THAT_CHANGE_AN_AGENT = {Outcome.ADDED, Outcome.REMOVED}


class AgentConnectionsView:
    def __init__(self, connections: list[AgentConnection]):
        self._connections = connections

    def lines(self, style: TextStyle) -> list[str]:
        if not self._connections:
            return ["No supported agents found.", style.dim(SUPPORTED_AGENTS_HINT)]
        lines = [self._line(connection, style) for connection in self._connections]
        if any(connection.outcome in OUTCOMES_THAT_CHANGE_AN_AGENT for connection in self._connections):
            lines.append(style.dim(RESTART_HINT))
        return lines

    def _line(self, connection: AgentConnection, style: TextStyle) -> str:
        name = style.bold(connection.title)
        config = home_abbreviated(connection.config)
        detail = f" {connection.detail}" if connection.detail else ""
        skill = home_abbreviated(connection.skill)
        installed_skill = f", skill in {skill}" if skill else ""
        removed_skill = f", removed the skill from {skill}" if skill else ""
        match connection.outcome:
            case Outcome.ADDED:
                return f"{style.green('✓')} {name}: added to {config}{installed_skill}{style.dim(detail)}"
            case Outcome.ALREADY_CONFIGURED:
                return f"{style.green('✓')} {name}: already configured in {config}{installed_skill}{style.dim(detail)}"
            case Outcome.REMOVED:
                return f"{style.green('✓')} {name}: removed from {config}{removed_skill}"
            case Outcome.NOT_CONFIGURED:
                return f"{style.dim('-')} {name}: not configured{removed_skill}"
            case Outcome.KEPT:
                return f"{style.dim('-')} {name}: left {config} alone,{detail}{removed_skill}"
            case Outcome.NOT_FOUND:
                return f"{style.dim('-')} {name}: not installed"
            case _:
                location = f"{config}: " if config else ""
                return f"{style.red('✗')} {name}: {location}{connection.detail}"
