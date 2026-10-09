# Claude Code Transcript Format

Read this only if the scripts fail or you need detail they did not extract.

## Where sessions live
- Folder: `$CLAUDE_CONFIG_DIR/projects/` if that variable is set, otherwise `~/.claude/projects/` (Windows: `%USERPROFILE%\.claude\projects\`).
- One subfolder per working directory. The folder name is the absolute path with separators and dots replaced by `-`, e.g. `/Users/saygin/dev/picky` becomes `-Users-saygin-dev-picky`. This encoding is lossy, so trust the `cwd` field inside the file, not the folder name.
- One file per session: `<session-uuid>.jsonl`. The newest session is the file with the latest modification time.
- Sessions started from the Claude desktop app's Code tab are stored the same way. When the desktop app runs a session in a git worktree, its `cwd` points inside a worktree folder (for example `<repo>/.claude/worktrees/<name>`), so it gets its own subfolder. Treat it as the same project.
- Subagent transcripts (files named `agent-*.jsonl`, or in a `subagents/` folder) and lines with `"isSidechain": true` are internal work by helper agents. Skip them unless the main session refers to their results.

## Line structure
Each line is one JSON object. Common fields: `type`, `uuid`, `parentUuid`, `sessionId`, `timestamp`, `cwd`, `gitBranch`, `isSidechain`, `isMeta`, `message`.

| `type` | What it is | What to read |
|---|---|---|
| `user` | A user prompt, or a tool result | `message.content` (string or list of blocks). If any block has `type: tool_result`, it is a tool result, not something the user typed. If `isMeta` is true, it is injected text, skip it. Text starting with `<command-` is a slash command record. |
| `assistant` | Claude's reply | `message.content` list: `text` blocks (what Claude said), `tool_use` blocks (`name`, `input`), `thinking` blocks (ignore) |
| `summary` | Auto summary of a compacted or resumed conversation | `summary` |
| `system` | System notices | usually ignore |
| others (e.g. `file-history-snapshot`) | internal bookkeeping | ignore |

## Tool calls worth reading
| Tool `name` | Useful `input` fields | Why it matters |
|---|---|---|
| `ExitPlanMode` | `plan` | The plan the user approved; often contains verification steps |
| `TodoWrite` | `todos[].content`, `todos[].status` | Last one is the final task list; `pending` items are unfinished work |
| `Edit`, `MultiEdit`, `Write`, `NotebookEdit` | `file_path` | Which files changed, where to look for regressions |
| `Bash` (or `PowerShell`) | `command`, `description` | How Claude started the app, ran tests, installed deps |
| `Task` / `Agent` | `prompt`, `description` | Work delegated to subagents |
| `WebFetch`, `Read`, `Grep`, `Glob` | paths and URLs | Context only |

## Quick manual extraction (if Python is unavailable)
macOS/Linux:
```
ls -t ~/.claude/projects/*/*.jsonl | head
grep -o '"cwd":"[^"]*"' <file> | head -1
```
Windows PowerShell:
```
Get-ChildItem $HOME\.claude\projects\*\*.jsonl | Sort-Object LastWriteTime -Descending | Select-Object -First 10 FullName, LastWriteTime
```
Then read the file and focus on the last assistant `text` blocks of the final turn; that is where Claude usually lists how to test.
