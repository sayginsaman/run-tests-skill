#!/usr/bin/env python3
"""List Claude Code session transcripts for a project, newest first.

Assumptions:
  - Claude Code (CLI and the Claude desktop app's Code tab) stores sessions as
    JSONL files at <config>/projects/<encoded-cwd>/<session-id>.jsonl, where
    <config> is $CLAUDE_CONFIG_DIR or ~/.claude.
  - Each user/assistant line carries a "cwd" field. We match on that instead of
    decoding folder names, because the encoding is lossy ("/" and "." both
    become "-") and desktop-app sessions may run inside git worktrees.

Extension points:
  - Extra search roots: set CLAUDE_SESSIONS_ROOTS to a path list
    (os.pathsep separated) of folders that contain a "projects" directory.

Usage:
  find_sessions.py                 # list most recently active projects
  find_sessions.py picky           # sessions whose cwd matches "picky"
  find_sessions.py /path/to/app --limit 3 --json
"""
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

PROMPT_PREVIEW = int(os.environ.get("RUN_TESTS_PROMPT_PREVIEW", "120"))
WORKTREE_MARKERS = (".claude/worktrees", ".claude-worktrees", "/worktrees/")


def config_roots():
    roots = []
    extra = os.environ.get("CLAUDE_SESSIONS_ROOTS")
    if extra:
        roots += [Path(p).expanduser() for p in extra.split(os.pathsep) if p]
    env = os.environ.get("CLAUDE_CONFIG_DIR")
    if env:
        roots.append(Path(env).expanduser())
    roots.append(Path.home() / ".claude")
    seen, out = set(), []
    for r in roots:
        key = str(r.resolve()) if r.exists() else str(r)
        if key not in seen and (r / "projects").is_dir():
            seen.add(key)
            out.append(r)
    return out


def text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(b.get("text", "") for b in content
                        if isinstance(b, dict) and b.get("type") == "text")
    return ""


def is_real_prompt(rec):
    if rec.get("type") != "user" or rec.get("isMeta") or rec.get("isSidechain"):
        return False
    msg = rec.get("message") or {}
    content = msg.get("content")
    if isinstance(content, list) and any(
            isinstance(b, dict) and b.get("type") == "tool_result" for b in content):
        return False
    t = text_of(content).strip()
    return bool(t) and not t.startswith("<command-") and not t.startswith("<local-command")


def scan_session(path):
    """Return metadata for one session file, or None if unreadable/empty."""
    info = {"path": str(path), "session_id": path.stem, "cwd": None,
            "branch": None, "first_prompt": "", "prompts": 0, "lines": 0}
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                info["lines"] += 1
                if '"user"' not in line and info["cwd"]:
                    continue  # cheap skip: only user lines matter after cwd is known
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                if not info["cwd"] and rec.get("cwd"):
                    info["cwd"] = rec["cwd"]
                if not info["branch"] and rec.get("gitBranch"):
                    info["branch"] = rec["gitBranch"]
                if is_real_prompt(rec):
                    info["prompts"] += 1
                    if not info["first_prompt"]:
                        t = " ".join(text_of(rec["message"].get("content")).split())
                        info["first_prompt"] = t[:PROMPT_PREVIEW]
    except OSError as exc:
        print(f"warning: cannot read {path}: {exc}", file=sys.stderr)
        return None
    if info["lines"] == 0:
        return None
    st = path.stat()
    info["modified"] = datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds")
    info["_mtime"] = st.st_mtime
    if not info["cwd"]:
        info["cwd"] = "(unknown, folder " + path.parent.name + ")"
    return info


def norm(p):
    return str(p).replace("\\", "/").rstrip("/").lower()


def repo_root_of(cwd):
    """Strip a worktree suffix so worktree sessions match their main repo."""
    n = norm(cwd)
    for marker in WORKTREE_MARKERS:
        idx = n.find(marker)
        if idx > 0:
            return n[:idx].rstrip("/")
    return n


def matches(cwd, query):
    q = norm(Path(query).expanduser()) if ("/" in query or "\\" in query) else query.lower()
    c, root = norm(cwd), repo_root_of(cwd)
    if q in (c, root):
        return 3
    if q in (c.rsplit("/", 1)[-1], root.rsplit("/", 1)[-1]):
        return 2
    if q in c:
        return 1
    return 0


def all_sessions():
    out = []
    for root in config_roots():
        for f in (root / "projects").glob("*/*.jsonl"):
            if f.name.startswith("agent-"):
                continue  # subagent sidechains, not top-level sessions
            s = scan_session(f)
            if s:
                out.append(s)
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("query", nargs="?", help="project name, path, or path fragment")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    roots = config_roots()
    if not roots:
        print("No Claude Code data folder found. Looked for a 'projects' folder in "
              "$CLAUDE_SESSIONS_ROOTS, $CLAUDE_CONFIG_DIR and ~/.claude.", file=sys.stderr)
        return 2

    sessions = all_sessions()
    if not args.query:
        latest = {}
        for s in sessions:
            key = repo_root_of(s["cwd"])
            if key not in latest or s["_mtime"] > latest[key]["_mtime"]:
                latest[key] = s
        rows = sorted(latest.values(), key=lambda s: s["_mtime"], reverse=True)[:args.limit]
        title = "Most recently active Claude Code projects"
    else:
        scored = [(matches(s["cwd"], args.query), s) for s in sessions]
        best = max((sc for sc, _ in scored), default=0)
        rows = [s for sc, s in scored if sc and sc == best]
        rows.sort(key=lambda s: s["_mtime"], reverse=True)
        rows = rows[:args.limit]
        title = f"Sessions matching '{args.query}'"

    for r in rows:
        r.pop("_mtime", None)
    if args.json:
        print(json.dumps(rows, indent=2))
        return 0 if rows else 1

    print(f"{title} (searched: {', '.join(str(r) for r in roots)})")
    if not rows:
        print("  none found")
        return 1
    projects = {repo_root_of(r["cwd"]) for r in rows}
    if args.query and len(projects) > 1:
        print(f"  NOTE: {len(projects)} different projects match. Ask the user which one.")
    for i, r in enumerate(rows, 1):
        print(f"\n[{i}] {r['modified']}  session {r['session_id']}")
        print(f"    cwd:     {r['cwd']}" + (f"  (branch {r['branch']})" if r["branch"] else ""))
        print(f"    prompts: {r['prompts']}  lines: {r['lines']}")
        print(f"    first:   {r['first_prompt'] or '(none)'}")
        print(f"    file:    {r['path']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
