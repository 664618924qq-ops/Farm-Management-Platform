# Optimized Acceptance Evidence Manifest

Package status: optimized acceptance-ready candidate / evidence included

This package is a new optimized acceptance candidate. It preserves the previous signed baseline package `livestock-monitor-user-acceptance-package-20260707-0041.zip` and does not overwrite it. The package updates archive metadata, delivery instructions, and evidence only; it does not modify platform or PC business code during packaging.

## PC Optimization Evidence

- `pc-client/docs/qa_pc_optimization_home_trend_current_20260707.png`
  - PC homepage trend panel evidence.
- `pc-client/docs/qa_pc_optimization_interval_dropdown_20260707.png`
  - PC 30/60 second interval dropdown evidence.
- `pc-client/docs/qa_pc_optimization_analysis_current_20260707.png`
  - PC analysis page evidence.
- `pc-client/docs/qa_pc_optimization_time_alignment_20260707.txt`
  - PC 30s/60s time-alignment samples and packet `DataTime` evidence.
  - Verified as readable ASCII/UTF-8 text before packaging.
- `pc-client/docs/qa_pc_optimization_responsiveness_20260707.txt`
  - PC responsiveness / anti-stutter evidence.

## Platform Evidence

- `logs/acceptance/tcp-acceptance-20260707-132313.json`
  - Latest packaging-time acceptance gate.
  - Expected result: `status = passed`, `ackValidation.cn = 9014`.
- `logs/acceptance/tcp-acceptance-20260707-124843.json`
  - Platform TCP gate result around 12:48.
  - Expected result: `status = passed`, `ackValidation.cn = 9014`.
- `logs/acceptance/tcp-acceptance-20260707-124848.json`
  - Platform TCP gate result around 12:48.
  - Expected result: `status = passed`, `ackValidation.cn = 9014`.
- `docs/product/progress-log.md`
  - Contains the QA-accepted 12:49 time-fix summary:
    - `DataTime=2026-07-07T12:49:34+08:00`
    - `receivedAtBeijing=2026-07-07T12:49:35+08:00`
    - `storedAtBeijing=2026-07-07T12:49:35+08:00`
  - Records `dataSource=database`, `timezone=Asia/Shanghai`, `recordCount=300`, `sensorCount=3`.

## Acceptance Notes

- Backend/TCP must be restarted before acceptance so the new receive-time logic is active.
- Historical records with the previous 8-hour time error are not backfilled; acceptance should verify newly received data only.
- Seed/demo data must not be used as the real acceptance basis. Use newly uploaded PC data and confirm MN/DataTime.
- SMS remains dry-run/noop by default. Real SMS provider access, keys, templates, and billing are reserved for a later delivery.

## Guard Commands

- Environment check: `powershell -NoProfile -ExecutionPolicy Bypass -File .\check-env.ps1`
- Port check: `powershell -NoProfile -ExecutionPolicy Bypass -File .\check-ports.ps1`
- Acceptance gate: `powershell -NoProfile -ExecutionPolicy Bypass -File .\check-acceptance.ps1 -SkipStartup`

## Package Lineage

- Previous signed baseline: `livestock-monitor-user-acceptance-package-20260707-0041.zip`
- New optimized candidate naming pattern: `livestock-monitor-optimized-acceptance-candidate-20260707-HHmm.zip`
