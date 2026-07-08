# Chrome and GitHub Workflow

## Chrome Usage

Use Chrome as the product acceptance and experience-testing entrance.

Recommended local acceptance URLs:

- Platform home: `http://127.0.0.1:5173`
- Data query: `http://127.0.0.1:5173/data-query`
- Protocol logs: `http://127.0.0.1:5173/protocol`
- Realtime monitoring: `http://127.0.0.1:5173/telemetry`
- Data analysis: `http://127.0.0.1:5173/analysis`
- Backend health: `http://127.0.0.1:8000/health`

Quick open command:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\open-chrome-acceptance.ps1
```

Acceptance focus:

- Data query should show factor names, not indicator codes.
- Factor name selector should support multi-select.
- CN=2011 and CN=2061 queries should both be checked.
- Protocol logs should use Beijing time, manual query, CN multi-select, and default day range.
- Realtime monitoring should refresh every 30 seconds and use real stored telemetry.
- Data analysis should use database records and provide readable suggestions.

## GitHub Usage In Chrome

Use GitHub in Chrome as the collaboration, code review, issue tracking, and release history entrance.

Recommended workflow:

- Track bugs with GitHub Issues using the bug report template.
- Track UX and product maturity ideas with the product optimization template.
- Use Pull Requests for platform, PC, QA, deployment, and documentation changes.
- Use GitHub Actions CI to run backend tests, frontend tests/build, and PC tests.
- Use GitHub Releases for zip acceptance packages instead of committing zip files to the repository.

Suggested labels:

- `bug`
- `product`
- `platform`
- `pc-client`
- `qa`
- `deployment`
- `p0`
- `p1`
- `p2`
- `p3`
- `needs-triage`

## Current Local Status

- The repository is initialized locally.
- No remote repository is configured yet.
- GitHub CLI is not currently available from PowerShell.
- The available GitHub client is a Chrome GitHub Web App shortcut:
  `C:\Users\DELL\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Chrome 应用\GitHub.lnk`.
- GitHub work should be done through Chrome/GitHub Web App rather than GitHub Desktop.

Before publishing:

1. Review `.gitignore` so local databases, virtual environments, zip packages, logs, and staging folders are not committed.
2. Create an initial commit with source code, docs, scripts, templates, and CI only.
3. Create the remote repository in Chrome GitHub Web App, preferably as a private repository unless the user explicitly wants it public.
4. Add the remote URL locally with `git remote add origin <repo-url>`, then push the initial branch.
5. Attach final zip packages to GitHub Releases rather than committing them.
