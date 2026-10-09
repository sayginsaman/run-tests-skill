# Report Template

Write the report to `<project>/.codex-test-runs/<timestamp>/report.md` using exactly this structure. Timestamp format: `YYYYMMDD-HHMM`.

```markdown
# Test Report: <project name>

- Date: <local date and time>
- Target: <URL or app name and how it was launched>
- Claude Code sessions read: <session id(s)>, <time span>
- Branch: <git branch>
- Mode: test-only | fix

## Summary
| Result | Count |
|---|---|
| PASS | n |
| FAIL | n |
| PARTIAL | n |
| FLAKY | n |
| BLOCKED | n |

Verdict: <one sentence, e.g. "The gluten-free filter works on desktop but breaks the map layout on mobile; persistence is missing as Claude noted.">

## What Claude Code built
<2 to 5 bullets from the transcript>

## Preflight (automated checks)
| Check | Command | Result |
|---|---|---|
| Unit tests | `npm test` | PASS (42/42) |

## Results
| ID | Test | Source | Result | Notes |
|---|---|---|---|---|
| T00 | App starts and home renders | CODEX | PASS | |
| T01 | Toggle gluten-free filter shows only GF places | CLAUDE | PASS | |
| T05 | Filter at 375px width | CODEX | FAIL | Toggle overlaps map controls |

## Failures in detail
### T05: Filter at 375px width
- Source: [CODEX] (user asked "make it work on mobile")
- Steps to reproduce:
  1. Open http://localhost:5173/map
  2. Set viewport to 375px wide
  3. Open the filter panel
- Expected: panel fits the screen, all controls tappable
- Actual: panel extends past the right edge, zoom buttons hidden underneath
- Evidence: <screenshot path or description>, console: <errors or "none">
- Category: Bug in new work | Regression | Pre-existing | Environment
- Suspected cause: `src/components/FilterPanel.tsx`, fixed width 420px

## Claude's checklist coverage
Every test or step Claude specified, with its result. Nothing Claude asked for may be missing from this list.
- [x] "toggle Gluten-free, you should see only GF restaurants" -> T01 PASS
- [ ] "persistence" (Claude said not yet implemented) -> T07 FAIL as expected

## Not tested
<anything skipped and why>

## Test data created
<accounts, records, files created during the run, so the user can clean up>

## Changes made (fix mode only)
<files changed and which test each fix addressed, with re-test result>

## Prompt for Claude Code
Paste this into Claude Code to fix the failures:

> Codex QA found these failures in <project> after the last session. Fix the root cause of each, keep changes minimal, and tell me how to re-verify.
> 1. T05 Filter panel overflows at 375px. Steps: ... Expected: ... Actual: ... Suspected: `src/components/FilterPanel.tsx`.
> 2. ...
```

Chat summary to the user after writing the file: the summary table, one line per FAIL/PARTIAL/BLOCKED, the report path, and the Claude Code prompt. Keep it short; the details live in the file.
