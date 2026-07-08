# 2026-07-07 Tonight Optimization Dispatch

## Context

The previous PM thread entered context compression and became unreliable. The current PM thread takes over tonight's optimization coordination.

Current baseline package:

- `livestock-monitor-optimized-acceptance-candidate-20260707-1323.zip`
- SHA256: `FCFAE4EBC16E51514738A7C5C109DEFD99D2FF0885E2334BD6ACA80E92502EFB`

Current 20-minute local sync task:

- Windows Scheduled Task: `LivestockProductSync20m`
- Log directory: `logs/pm-sync/`
- Latest successful manual run at setup time: `pm-sync-20260707-202837.log`
- Latest acceptance evidence at setup time: `logs/acceptance/tcp-acceptance-20260707-203042.json`

## Team Assignments

### QA / Automation Test Engineer

Thread: `019f357b-69b6-70b0-a434-26a3e23f4a00`

Mission tonight: complete optimization-stage functional testing and find real product bugs.

Use `docs/change-request-qa-test-plan.md` as the master QA plan. Also check every new `logs/pm-sync/pm-sync-*.log` file.

Required commands:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\check-ports.ps1
.\backend\.venv\Scripts\python.exe tools\continuous_test.py --root .
cd .\pc-client
.\.venv\Scripts\python.exe -m pytest tests -q
cd ..
powershell -NoProfile -ExecutionPolicy Bypass -File .\check-acceptance.ps1 -SkipStartup
```

Important: PC tests must run from `pc-client`; running them from repo root causes `ModuleNotFoundError: app` and should not be reported as a product bug.

Coverage tonight:

- PC duplicate upload prevention.
- 30/60 second save interval.
- ACK display and `CN=9014` validation.
- `CN=2011`, `CN=2061`, protocol log accepted status.
- DataTime alignment and Beijing time semantics.
- Dashboard, protocol logs, realtime monitoring, data query, data analysis, alerts, inspections.
- Chinese labels and useful error states.
- Package evidence and acceptance JSON.

Report format:

- Severity: P0 / P1 / P2.
- Area: PC / platform / deployment / QA-test / documentation / experience.
- Reproduction steps.
- Actual result.
- Expected result.
- Evidence path.
- Suggested owner.

QA may directly fix QA-owned scripts, acceptance scripts, docs, evidence organization, and report formatting. Product or business-code defects must be returned to PM for dispatch.

### Product Experience Officer

Thread: `019f36ec-9d7a-7822-b50d-1cf66b3f6215`

Mission tonight: complete user-path experience review, focusing on whether the product is understandable, usable, and explainable in front of a customer.

Review focus:

- Login page: whether `admin / admin123` is clear.
- Dashboard: whether users can immediately see PC data was received and ACK succeeded.
- Technical phrases: whether `valid_9014_ack` / `CN=9014 ACK returned` need user-facing Chinese explanation.
- Protocol logs: max 100 rows, no pagination/count hint; judge whether this confuses users.
- Data query: max 300 rows, no pagination/count hint; judge whether scanning is hard.
- Realtime monitoring: whether demo/history data and new PC data are distinguishable.
- Data analysis: whether `0.0` and `疑似恒值` are understandable or misleading.
- SMS `dry-run/noop`: whether the boundary is clear.

Report format:

- Blocker experience issue.
- Must fix tonight.
- Should improve.
- Later optimization.
- Recommended user-facing copy.

### PC Developer

Thread: `019f3501-6159-7d91-a494-899dec8911a9`

Mission tonight: stay ready for QA/experience P0/P1 PC-side fixes. Do not expand unrelated features.

Respond only to:

- Duplicate packet upload.
- 30/60 second interval behavior.
- ACK display or timeout behavior.
- DataTime rounding and local DB/upload packet consistency.
- Homepage trend readability.
- Data analysis page readability.
- Startup stutter or long non-responsive state.

Expected response for each assigned issue:

- Root cause.
- Files changed.
- Verification command and result.
- Remaining risk.

### Platform Developer

Thread: `019f26d1-0276-7f33-b77a-29641bec570e`

Mission tonight: stay ready for QA/experience P0/P1 platform-side fixes. Do not expand unrelated features.

Respond only to:

- Protocol log query or CN multi-select behavior.
- Default time and Beijing time semantics.
- Data source clarity: real PC data vs seed/demo/history data.
- Realtime monitoring 30-second refresh and real data path.
- Data query/data analysis volume, readability, or performance.
- Alert and inspection Chinese labels/useful information.
- Sticky left menu or page layout blocking operations.

Expected response for each assigned issue:

- Root cause.
- Files changed.
- API/page evidence.
- Test/build/acceptance result.
- Remaining risk.

### Deployment / Packaging Engineer

Thread: `019f36ee-6682-7581-b315-3a0f873ab9fa`

Mission tonight: keep the current optimized candidate stable and help diagnose environment/package failures. Do not repackage unless PM asks.

Current package:

- `livestock-monitor-optimized-acceptance-candidate-20260707-1323.zip`

Respond only to:

- Zip corruption.
- Missing critical package files.
- `VERSION.txt`, manifest, or acceptance guide mismatch.
- Startup script failure.
- Environment/port/dependency failure.
- `check-acceptance.ps1 -SkipStartup` failure.
- QA requests for package evidence repair.

Every response must include:

- Affected artifact.
- Whether current zip remains valid.
- Command run and result.
- Whether repackaging is required.

## PM Triage Rules

- P0: blocks user re-acceptance. Dispatch immediately and rerun acceptance gate after fix.
- P1: must fix in this optimization round. Dispatch to owner and verify in the next 20-minute sync.
- P2: record for later optimization; do not interrupt tonight unless it affects customer trust.

## Tonight Red Lines

- No silent repackage.
- No overwriting the previous baseline package.
- No using seed/demo data as real acceptance evidence.
- No passing if `CN=9014` ACK is invalid or missing.
- No passing if backend/TCP restart prerequisite is ignored for time-fix verification.
- No claiming real SMS delivery; current SMS is `dry-run/noop` only.
