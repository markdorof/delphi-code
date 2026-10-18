# Delphi Code

<!-- mcp-name: io.github.markdorof/delphi-code -->

Let your coding agent browse code across all your repositories. Index local projects and GitHub or Bitbucket repositories, then ask "where does the backend handle the refund the web app requests?" and get the right files from every repository at once, even when no file contains those words.

![Claude Code, opened in one service, is asked whether an endpoint can be removed and finds its only caller in another repository](https://raw.githubusercontent.com/markdorof/delphi-code/main/docs/demo.gif)

- **Private:** your code never leaves your machine. Indexing and search run offline with a local model; no account, cloud provider, or background daemon.
- **Fast:** the MCP server keeps the model loaded, so repeated searches are near-instant. No GPU needed.
- **Works with your agents:** Claude Code, Claude Desktop, Codex, Cursor, VS Code, Gemini CLI, and OpenCode.

## Install

```sh
curl -LsSf https://github.com/markdorof/delphi-code/releases/latest/download/install.sh | sh
```

The script installs [uv](https://docs.astral.sh/uv/) if needed, then runs `setup`, which downloads the embedding model once and connects every agent it finds. Options go after `sh -s --`: `--no-setup`, `--no-connect`, `--version VERSION`. With uv already installed:

```sh
uv tool install --managed-python --python 3.14 delphi-code
delphi-code setup
```

Requires macOS 14+ on Apple silicon (Linux is untested, Windows unsupported). `delphi-code doctor` checks the installation.

## Use

```sh
delphi-code add ~/src/api github.com/octo/tools   # track and index projects
delphi-code search 'where are user passwords checked?'
delphi-code ui                                     # or do it all in the browser
```

Your agent calls the same search through MCP. After installing a new agent, run `delphi-code connect`. To connect one by hand:

| Agent | Setup |
|---|---|
| Claude Code | `claude plugin marketplace add markdorof/delphi-code`, then `claude plugin install delphi-code@delphi-code` |
| Codex | `codex plugin marketplace add markdorof/delphi-code`, then `codex plugin add delphi-code@delphi-code` |
| Cursor | Add `{"mcpServers": {"delphi-code": {"type": "stdio", "command": "delphi-code", "args": ["mcp"]}}}` to `~/.cursor/mcp.json` |
| VS Code (Copilot) | `code --add-mcp '{"name": "delphi-code", "command": "delphi-code", "args": ["mcp"]}'` |
| Gemini CLI | `gemini mcp add delphi-code delphi-code mcp` |
| OpenCode | Add `{"mcp": {"delphi-code": {"type": "local", "command": ["delphi-code", "mcp"]}}}` to `~/.config/opencode/opencode.json` |

For agents other than Claude Code and Codex, also copy the [skill](https://github.com/markdorof/delphi-code/blob/main/plugin/skills/delphi-code/SKILL.md) into the agent's skills folder so it knows when to search by meaning instead of grep.

## Commands

| Command | What it does |
|---|---|
| `setup` | Downloads the model (or imports it with `--from DIR` on an offline machine) and connects agents. |
| `add [SOURCE ...]` | Tracks and indexes local paths or remote repositories (`--ref` picks a branch or tag). Without sources, picks repositories from your GitHub or Bitbucket account. |
| `sync [PROJECT ...]` | Updates tracked projects, re-embedding only what changed. |
| `index -p PATH` | Indexes a project once without tracking it. |
| `search QUERY` | Searches every index, or one with `-p`. Filter with `--language`, `--path`, `--limit`. |
| `list`, `status`, `remove NAME` | Show tracked projects, show a project's index, stop tracking a project. |
| `connect`, `disconnect` | Add or remove Delphi Code in your agents' configs. |
| `ui` | Opens a local web UI for search, projects, and setup checks. |
| `doctor` | Checks the model and storage. |
| `mcp` | Serves the commands as MCP tools over stdio. |

`-p` takes a path or an indexed project's name. `index` and `add` skip `.gitignore`d files and accept `--ignore`, `--path`, and `--language`. Every command takes `--help`, and most take `--json` for scripts. Only `setup`, `add`, and `sync` use the network.

## Settings

| Variable | Purpose |
|---|---|
| `GITHUB_TOKEN` / `GH_TOKEN` | GitHub access for remote repositories (falls back to `gh auth token`, then git's credentials) |
| `BITBUCKET_APP_PASSWORD` with `BITBUCKET_EMAIL` or `BITBUCKET_USERNAME` | Bitbucket access (an API token works) |
| `DELPHI_CODE_MODEL` | Use another local SentenceTransformers model instead of the default all-MiniLM-L6-v2 |
| `DELPHI_CODE_INDEX_ROOT`, `DELPHI_CODE_REGISTRY`, `DELPHI_CODE_LOG_FILE` | Move indexes, the tracked-project list, or the log |
| `DELPHI_CODE_LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `OFF` |

Data lives in `~/Library/Application Support/delphi-code` on macOS and `~/.local/share/delphi-code` on Linux.

## Upgrade and uninstall

```sh
uv tool upgrade delphi-code
```

Your model and indexes are kept. If a command fails with `index_incompatible`, delete the index directory it names and run `sync` again. See [releases](https://github.com/markdorof/delphi-code/releases) for changes.

```sh
delphi-code disconnect
uv tool uninstall delphi-code
rm -rf ~/Library/Application\ Support/delphi-code
uv cache clean   # frees about 900 MB of downloaded packages
```

If the install script installed uv and you don't need it, [uninstall uv](https://docs.astral.sh/uv/getting-started/installation/#uninstallation) and its Python too.

## License

Apache-2.0. See [THIRD_PARTY_NOTICES.md](https://github.com/markdorof/delphi-code/blob/main/THIRD_PARTY_NOTICES.md). To contribute, see [CONTRIBUTING.md](https://github.com/markdorof/delphi-code/blob/main/CONTRIBUTING.md).
