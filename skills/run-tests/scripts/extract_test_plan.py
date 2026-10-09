#!/usr/bin/env python3
"""Condense Claude Code session transcripts into a testing digest (Markdown).

Assumptions:
  - Input files are Claude Code JSONL transcripts (see
    references/transcript-format.md). Unknown record types are ignored, so
    format additions do not break extraction.
  - Pass sessions newest first; the digest presents them oldest first so the
    story reads in order.

Extension points:
  - TEST_HINTS / RUN_HINTS below control which passages and commands are
    flagged. Override with RUN_TESTS_EXTRA_HINTS (comma separated words).
  - --max-chars caps each quoted passage; --max-items caps each list.

Usage:
  extract_test_plan.py newest.jsonl [older.jsonl ...] [--out digest.md]
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

TEST_HINTS = ["test", "verify", "verif", "check that", "make sure", "should see",
              "you should", "try ", "manual", "qa", "acceptance", "expected",
              "reproduce", "steps", "confirm", "smoke", "regression", "edge case",
              "not tested", "untested", "todo", "mock", "stub", "placeholder",
              "known issue", "limitation", "doesn't yet", "not yet", "follow-up"]
TEST_HINTS += [h.strip().lower() for h in
               os.environ.get("RUN_TESTS_EXTRA_HINTS", "").split(",") if h.strip()]

RUN_HINTS = {
    "dev-server": re.compile(r"\b(npm|pnpm|yarn|bun)\s+(run\s+)?(dev|start|serve|preview)\b|"
                             r"\b(vite|next dev|expo start|flask run|uvicorn|rails s|"
                             r"python[0-9.]*\s+-m\s+http\.server|electron|tauri dev|"
                             r"manage\.py runserver|docker compose up|php artisan serve)\b"),
    "test": re.compile(r"\b(test|tests|jest|vitest|pytest|playwright|cypress|mocha|"
                       r"go test|cargo test|xcodebuild test|gradlew test)\b"),
    "build": re.compile(r"\b(build|tsc|lint|eslint|typecheck|type-check|mypy|ruff)\b"),
    "install": re.compile(r"\b(npm|pnpm|yarn|bun)\s+(i|install|add)\b|pip install|"
                          r"poetry install|bundle install"),
}
URL_RE = re.compile(r"https?://(?:localhost|127\.0\.0\.1|0\.0\.0\.0|\[::1\]|[\w.-]+\.(?:local|test))"
                    r"(?::\d+)?[^\s)\"'`<>]*|\blocalhost:\d+[^\s)\"'`<>]*|\bport\s+\d{2,5}\b",
                    re.IGNORECASE)
EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit", "str_replace_based_edit_tool"}


def text_blocks(content):
    if isinstance(content, str):
        return [content]
    out = []
    if isinstance(content, list):
        for b in content:
            if isinstance(b, dict) and b.get("type") == "text" and b.get("text"):
                out.append(b["text"])
    return out


def clip(s, n):
    s = s.strip()
    return s if len(s) <= n else s[:n].rstrip() + " [...]"


def paragraphs(text):
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def is_testy(p):
    low = p.lower()
    return any(h in low for h in TEST_HINTS)


def load(path):
    recs = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for ln, line in enumerate(fh, 1):
            try:
                recs.append(json.loads(line))
            except ValueError:
                print(f"warning: {path}:{ln} is not valid JSON, skipped", file=sys.stderr)
    return recs


def digest_session(path, max_chars, max_items):
    recs = load(path)
    meta = {"file": str(path), "id": Path(path).stem, "cwd": None, "branch": None,
            "start": None, "end": None}
    prompts, plans, summaries, testy, files, commands, urls = [], [], [], [], {}, [], set()
    todos, final_text, last_assistant_texts = None, "", []

    for r in recs:
        if r.get("isSidechain"):
            continue
        meta["cwd"] = meta["cwd"] or r.get("cwd")
        meta["branch"] = meta["branch"] or r.get("gitBranch")
        ts = r.get("timestamp")
        if ts:
            meta["start"] = meta["start"] or ts
            meta["end"] = ts
        rtype = r.get("type")
        if rtype == "summary" and r.get("summary"):
            summaries.append(r["summary"])
            continue
        msg = r.get("message") or {}
        content = msg.get("content")

        if rtype == "user" and not r.get("isMeta"):
            if isinstance(content, list) and any(
                    isinstance(b, dict) and b.get("type") == "tool_result" for b in content):
                continue
            for t in text_blocks(content):
                t = t.strip()
                if t and not t.startswith("<command-") and not t.startswith("<local-command"):
                    prompts.append(clip(t, max_chars))
                    for u in URL_RE.findall(t):
                        urls.add(u.rstrip(".,;:!?"))
                    last_assistant_texts = []  # new turn
        elif rtype == "assistant" and isinstance(content, list):
            for b in content:
                if not isinstance(b, dict):
                    continue
                bt = b.get("type")
                if bt == "text" and b.get("text"):
                    t = b["text"]
                    last_assistant_texts.append(t)
                    final_text = "\n\n".join(last_assistant_texts)
                    for u in URL_RE.findall(t):
                        urls.add(u.rstrip(".,;:!?"))
                    for p in paragraphs(t):
                        if is_testy(p):
                            testy.append(clip(p, max_chars))
                elif bt == "tool_use":
                    name, inp = b.get("name", ""), b.get("input") or {}
                    if name == "ExitPlanMode" and inp.get("plan"):
                        plans.append(clip(inp["plan"], max_chars * 4))
                    elif name == "TodoWrite" and isinstance(inp.get("todos"), list):
                        todos = inp["todos"]
                    elif name in EDIT_TOOLS:
                        fp = inp.get("file_path") or inp.get("notebook_path") or inp.get("path")
                        if fp:
                            files[fp] = files.get(fp, 0) + 1
                    elif name in ("Bash", "PowerShell") and inp.get("command"):
                        cmd = " ".join(str(inp["command"]).split())
                        tags = [k for k, rx in RUN_HINTS.items() if rx.search(cmd)]
                        commands.append((clip(cmd, 300), tags, inp.get("description", "")))
                        for u in URL_RE.findall(cmd):
                            urls.add(u.rstrip(".,;:!?"))

    # de-duplicate while keeping order
    def uniq(seq):
        seen, out = set(), []
        for x in seq:
            k = x if isinstance(x, str) else x[0]
            if k not in seen:
                seen.add(k)
                out.append(x)
        return out

    return {"meta": meta, "summaries": uniq(summaries), "prompts": prompts,
            "plans": plans, "todos": todos, "files": files,
            "commands": uniq(commands), "urls": sorted(urls),
            "testy": uniq(testy)[-max_items:], "final": final_text}


def render(d, max_items):
    m = d["meta"]
    out = [f"## Session {m['id']}",
           f"- File: `{m['file']}`",
           f"- Working directory: `{m['cwd']}`" + (f" (branch `{m['branch']}`)" if m["branch"] else ""),
           f"- Time span: {m['start']} to {m['end']}", ""]
    if d["summaries"]:
        out += ["### Session summaries (from Claude Code)"] + [f"- {s}" for s in d["summaries"]] + [""]
    out += ["### User requests (acceptance criteria)"]
    out += [f"{i}. {p}" for i, p in enumerate(d["prompts"][:max_items], 1)] or ["(none)"]
    if len(d["prompts"]) > max_items:
        out.append(f"... {len(d['prompts']) - max_items} more not shown")
    out.append("")
    if d["plans"]:
        out += ["### Approved plans"] + [f"```\n{p}\n```" for p in d["plans"]] + [""]
    if d["todos"]:
        out += ["### Final todo list"]
        out += [f"- [{t.get('status', '?')}] {t.get('content', '')}" for t in d["todos"]] + [""]
    out += ["### Files changed (edit count)"]
    out += [f"- `{f}` ({n})" for f, n in sorted(d["files"].items(), key=lambda x: -x[1])] or ["(none)"]
    out.append("")
    out += ["### Shell commands run"]
    if d["commands"]:
        for cmd, tags, desc in d["commands"][-max_items:]:
            tag = f"[{', '.join(tags)}] " if tags else ""
            out.append(f"- {tag}`{cmd}`" + (f" - {desc}" if desc else ""))
    else:
        out.append("(none)")
    out.append("")
    out += ["### URLs and ports mentioned"] + ([f"- {u}" for u in d["urls"]] or ["(none)"]) + [""]
    out += ["### Assistant passages about testing, verification or gaps"]
    out += [f"> {p.replace(chr(10), chr(10) + '> ')}\n" for p in d["testy"]] or ["(none)"]
    out += ["", "### Claude's final message (verbatim)", "```", d["final"].strip() or "(none)", "```", ""]
    return "\n".join(out)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sessions", nargs="+", help="JSONL files, newest first")
    ap.add_argument("--out", help="write digest here instead of stdout")
    ap.add_argument("--max-chars", type=int, default=int(os.environ.get("RUN_TESTS_MAX_CHARS", "1500")))
    ap.add_argument("--max-items", type=int, default=int(os.environ.get("RUN_TESTS_MAX_ITEMS", "60")))
    args = ap.parse_args()

    parts = ["# Claude Code testing digest",
             f"Sessions: {len(args.sessions)} (shown oldest first)", ""]
    for p in reversed(args.sessions):
        if not Path(p).is_file():
            print(f"error: session file not found: {p}", file=sys.stderr)
            return 2
        parts.append(render(digest_session(p, args.max_chars, args.max_items), args.max_items))
    text = "\n".join(parts)

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        print(f"Digest written to {out} ({len(text)} chars)")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
