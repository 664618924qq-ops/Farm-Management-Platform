# PM 20-Minute Sync Runbook - 2026-07-07

## Purpose

Codex thread dispatch and built-in automation tools were not exposed in the takeover thread. To keep tonight's optimization work moving, the PM created a Windows Scheduled Task that runs the acceptance check chain every 20 minutes and writes logs under the project.

## Scheduled Task

Task name:

```powershell
LivestockProductSync20m
```

Check task state:

```powershell
Get-ScheduledTask -TaskName LivestockProductSync20m
Get-ScheduledTaskInfo -TaskName LivestockProductSync20m
```

Stop the task:

```powershell
Unregister-ScheduledTask -TaskName LivestockProductSync20m -Confirm:$false
```

## Log Location

```text
C:\Users\DELL\Documents\Codex project\logs\pm-sync
```

Get the latest log:

```powershell
Get-ChildItem "C:\Users\DELL\Documents\Codex project\logs\pm-sync" -File |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1
```

Read the latest log tail:

```powershell
$latest = Get-ChildItem "C:\Users\DELL\Documents\Codex project\logs\pm-sync" -File |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1
Get-Content -LiteralPath $latest.FullName -Tail 80
```

## Check Chain

The scheduled task runs:

1. Port check

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\check-ports.ps1
```

2. Backend/frontend continuous tests

```powershell
.\backend\.venv\Scripts\python.exe tools\continuous_test.py --root .
```

3. PC client tests

```powershell
cd .\pc-client
.\.venv\Scripts\python.exe -m pytest tests -q
cd ..
```

4. Real TCP acceptance gate

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\check-acceptance.ps1 -SkipStartup
```

## Expected PASS Evidence

A healthy cycle should show:

- `check-ports.ps1`: MySQL OK. Backend/TCP/Web listeners may show warning because they are already running; this is expected before startup if PIDs are known.
- `continuous_test.py`: backend PASS, frontend-test PASS, frontend-build PASS.
- PC tests: `73 passed`.
- acceptance gate: `status=passed`, `ackValidation.valid=true`, `ackValidation.cn=9014`, `protocolLog.status=accepted`.

## Failure Dispatch Rules

### Port or startup failure

Owner: Deployment `019f36ee-6682-7581-b315-3a0f873ab9fa`

Dispatch when:

- MySQL is not reachable.
- Backend 8000 is not healthy.
- TCP 9100 is not listening.
- Web 5173 is not listening.
- A startup script fails.

### Backend/frontend test failure

Owner: Platform `019f26d1-0276-7f33-b77a-29641bec570e`

Dispatch when:

- Backend pytest fails.
- Frontend test fails.
- Frontend build fails.
- Data query, protocol log, analysis, alert, inspection, or page route behavior fails.

### PC test failure

Owner: PC `019f3501-6159-7d91-a494-899dec8911a9`

Dispatch when:

- `pc-client` tests fail when run from the correct directory.
- Duplicate upload, interval, ACK, DataTime, local DB, homepage trend, or PC analysis behavior fails.

### Real TCP acceptance failure

Primary owner: QA `019f357b-69b6-70b0-a434-26a3e23f4a00`

QA triages first and assigns:

- `connection`: deployment or platform.
- `protocol`: platform or PC depending on packet source.
- `acknowledgement`: platform and PC both inspect.
- `ui evidence`: QA/product experience.

### User experience issue with passing checks

Owner: Product Experience `019f36ec-9d7a-7822-b50d-1cf66b3f6215`

Dispatch when checks pass but users may still be confused by:

- Technical ACK wording.
- Large unpaginated tables.
- Demo/history data mixed with real PC data.
- `0.0` values and `疑似恒值` explanation.
- SMS dry-run/noop boundary.

## PM Cycle Agenda

Every 20 minutes:

1. Read the newest `logs/pm-sync/pm-sync-*.log`.
2. Confirm whether all four check-chain steps passed.
3. Read QA and product-experience feedback if available.
4. Classify findings as P0/P1/P2.
5. Dispatch P0/P1 to PC, platform, or deployment.
6. Keep P2 in later optimization unless it affects customer trust.
7. Record the cycle result in `docs/product/progress-log.md` when editing tools are available.

## Current Known Non-Blocking Risks

- Protocol log shows up to 100 rows without pagination/count prompt.
- Data query can request up to 300 rows without pagination/count prompt.
- Realtime monitoring can show demo/history data alongside real PC data.
- Data analysis may show many `0.0` values and `疑似恒值`; this needs clear explanation.
- SMS is dry-run/noop only.
