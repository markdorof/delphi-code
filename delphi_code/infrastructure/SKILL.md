---
name: delphi-code
description: Semantic code search over locally indexed projects with the delphi-code CLI. Use when looking for code by what it does rather than by an exact name — "where are passwords checked?", "how is retry handled?" — when you don't know which file or identifier to grep for, or when searching across several repositories at once.
---

# Delphi Code semantic search

`delphi-code` answers natural-language questions about code from a local index. It runs offline.

If the `delphi-code` MCP tools (`search`, `index`, `status`, and the rest) are available, use them: they take the same options as the CLI commands below and answer in milliseconds, because the server keeps the model loaded. Otherwise run the CLI, which loads the model on every call.

## When to use it instead of grep

- You know the behaviour or concept but not the identifier: "where is the session token refreshed?"
- The codebase is unfamiliar and you need a starting point before reading files.
- The answer may live in another repository the user has indexed.

Use grep or file search instead when you already know an exact name, string, or path. A good pattern is to run a semantic search first to find the right files, then grep inside them.

## Searching

```sh
delphi-code search --json -p /absolute/path/to/project 'where are user passwords checked?'
```

- `-p` takes a path, an indexed key (`github.com/acme/api`), or a folder name (`api`). Leave it out to search every indexed project. The current directory is **not** the default for `search`.
- Phrase the query the way you would ask a colleague: describe the behaviour, not a single keyword.
- Narrow the results with `--language python`, `--path 'src/*'` (both repeatable), and `--limit N` (default 10).

The output is one JSON object. Results are in `data.results`, best match first:

```json
{"ok": true, "data": {"results": [
  {"path": "auth/passwords.py", "start_line": 17, "end_line": 31, "score": 0.52, "language": "python", "text": "..."}
]}}
```

When you search every project, each result also has `project` (an absolute path, or null for a remote repository) and `key`. `path` is relative to the project root. A higher `score` is a closer match. Scores are relative, so compare results with each other rather than against a fixed threshold. Open the files you find and read around `start_line` before drawing conclusions.

## Keeping the index current

```sh
delphi-code status --json -p /absolute/path/to/project    # is it indexed, and when?
delphi-code index --json -p /absolute/path/to/project     # build or incrementally update
delphi-code list --json --indexed                         # which projects are indexed
```

Indexes don't update on their own. After you edit files, run `index` before searching if the results should include your changes; it's incremental, so this is cheap. The first index of a large project can take minutes.

## Errors

On failure, `ok` is false and `error.code` and `error.message` say what went wrong. The exit codes are:

| Exit | Meaning | What to do |
|---|---|---|
| 2 | Bad arguments or unknown project | Fix `-p` or the options |
| 3 | Model missing | Ask the user to run `delphi-code setup` (it downloads the model) |
| 4 | No index, or an incompatible one | Run `delphi-code index -p <project>`, or follow the message |
| 5 | Index busy or another failure | Retry shortly, or report the message |

If `delphi-code` is not installed, tell the user it can be installed with `uv tool install --managed-python delphi-code && delphi-code setup`. Don't install it yourself without asking.
