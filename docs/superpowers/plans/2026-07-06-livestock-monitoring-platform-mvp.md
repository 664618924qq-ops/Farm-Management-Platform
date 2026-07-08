# Livestock Monitoring Platform MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a runnable MVP for a multi-farm livestock environment monitoring platform with web management, telemetry visualization, alert handling, inspection records, and TCP ingestion.

**Architecture:** The repository will contain a `FastAPI` backend and a `Vue 3` frontend in separate folders. The backend owns business APIs, MySQL persistence, alert evaluation, and a simple JSON-over-TCP receiver. The frontend provides a role-oriented dashboard and CRUD screens that consume the backend API.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, Pydantic, pytest, Vue 3, Vite, TypeScript, Pinia, Vue Router, Element Plus, ECharts

---

## File Structure

- `backend/`
  Python API service, TCP receiver, tests, and local development config.
- `frontend/`
  Vue application, routes, UI layout, charts, and API wrappers.
- `docs/superpowers/specs/`
  Approved design specification.
- `docs/superpowers/plans/`
  Implementation plan and execution record.

### Task 1: Scaffold Backend Foundation

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/main.py`
- Create: `backend/app/core/config.py`
- Create: `backend/app/db/base.py`
- Create: `backend/app/db/session.py`
- Create: `backend/tests/test_health.py`

- [ ] **Step 1: Write the failing test**

```python
from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint_returns_ok() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_health.py -q`
Expected: FAIL because `app.main` or `/health` does not exist.

- [ ] **Step 3: Write minimal implementation**

```python
from fastapi import FastAPI

app = FastAPI()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_health.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend
git commit -m "feat: scaffold backend service"
```

### Task 2: Add Core Domain Models and Seed API

**Files:**
- Create: `backend/app/models/farm.py`
- Create: `backend/app/models/shed.py`
- Create: `backend/app/models/device.py`
- Create: `backend/app/models/sensor.py`
- Create: `backend/app/models/telemetry.py`
- Create: `backend/app/models/alert.py`
- Create: `backend/app/models/inspection.py`
- Create: `backend/app/models/user.py`
- Create: `backend/app/api/routes/dashboard.py`
- Create: `backend/app/api/routes/farms.py`
- Create: `backend/app/api/router.py`
- Create: `backend/tests/test_dashboard.py`

- [ ] **Step 1: Write the failing test**

```python
from fastapi.testclient import TestClient

from app.main import app


def test_dashboard_summary_returns_expected_keys() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/dashboard/summary")

    data = response.json()
    assert response.status_code == 200
    assert "farmCount" in data
    assert "shedCount" in data
    assert "onlineDeviceCount" in data
    assert "activeAlertCount" in data
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_dashboard.py -q`
Expected: FAIL because route is missing.

- [ ] **Step 3: Write minimal implementation**

```python
from fastapi import APIRouter

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
def dashboard_summary() -> dict[str, int]:
    return {
        "farmCount": 0,
        "shedCount": 0,
        "onlineDeviceCount": 0,
        "activeAlertCount": 0,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_dashboard.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend
git commit -m "feat: add domain models and dashboard route"
```

### Task 3: Add TCP Telemetry Ingestion and Alert Evaluation

**Files:**
- Create: `backend/app/services/telemetry_ingestion.py`
- Create: `backend/app/services/alert_service.py`
- Create: `backend/app/tcp/server.py`
- Create: `backend/tests/test_telemetry_ingestion.py`

- [ ] **Step 1: Write the failing test**

```python
from app.services.telemetry_ingestion import normalize_payload


def test_normalize_payload_returns_device_and_metrics() -> None:
    payload = {
        "farmCode": "FARM-001",
        "shedCode": "SHED-001",
        "deviceCode": "DEV-001",
        "reportedAt": "2026-07-06T10:00:00+08:00",
        "metrics": [{"code": "temperature", "value": 28.5, "unit": "C"}],
    }

    normalized = normalize_payload(payload)

    assert normalized.device_code == "DEV-001"
    assert normalized.metrics[0].code == "temperature"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_telemetry_ingestion.py -q`
Expected: FAIL because ingestion service is missing.

- [ ] **Step 3: Write minimal implementation**

```python
from pydantic import BaseModel


class MetricReading(BaseModel):
    code: str
    value: float
    unit: str


class NormalizedTelemetry(BaseModel):
    device_code: str
    metrics: list[MetricReading]


def normalize_payload(payload: dict) -> NormalizedTelemetry:
    metrics = [MetricReading(**item) for item in payload["metrics"]]
    return NormalizedTelemetry(device_code=payload["deviceCode"], metrics=metrics)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_telemetry_ingestion.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend
git commit -m "feat: add telemetry ingestion service"
```

### Task 4: Scaffold Frontend App Shell

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/src/main.ts`
- Create: `frontend/src/App.vue`
- Create: `frontend/src/router/index.ts`
- Create: `frontend/src/layouts/AppLayout.vue`
- Create: `frontend/src/views/DashboardView.vue`
- Create: `frontend/src/views/FarmsView.vue`
- Create: `frontend/src/views/AlertsView.vue`
- Create: `frontend/src/views/InspectionsView.vue`

- [ ] **Step 1: Write the failing test**

```ts
import { describe, expect, it } from "vitest";

import { routes } from "../src/router";

describe("router", () => {
  it("includes dashboard route", () => {
    expect(routes.some((route) => route.path === "/dashboard")).toBe(true);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm --prefix frontend run test -- router`
Expected: FAIL because frontend app is missing.

- [ ] **Step 3: Write minimal implementation**

```ts
export const routes = [
  { path: "/", redirect: "/dashboard" },
  { path: "/dashboard", component: DashboardView },
];
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm --prefix frontend run test -- router`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend
git commit -m "feat: scaffold frontend app shell"
```

### Task 5: Build Core CRUD Views and Charts

**Files:**
- Create: `frontend/src/components/dashboard/MetricCard.vue`
- Create: `frontend/src/components/dashboard/TrendChart.vue`
- Create: `frontend/src/components/forms/FarmFormDrawer.vue`
- Create: `frontend/src/components/forms/DeviceFormDrawer.vue`
- Create: `frontend/src/stores/dashboard.ts`
- Create: `frontend/src/api/client.ts`
- Modify: `frontend/src/views/DashboardView.vue`
- Modify: `frontend/src/views/FarmsView.vue`
- Modify: `frontend/src/views/AlertsView.vue`
- Modify: `frontend/src/views/InspectionsView.vue`

- [ ] **Step 1: Write the failing test**

```ts
import { render, screen } from "@testing-library/vue";

import DashboardView from "../src/views/DashboardView.vue";

test("shows dashboard title", () => {
  render(DashboardView);

  expect(screen.getByText("养殖场监测总览")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm --prefix frontend run test -- dashboard`
Expected: FAIL because the view does not render the expected content.

- [ ] **Step 3: Write minimal implementation**

```vue
<template>
  <section>
    <h1>养殖场监测总览</h1>
  </section>
</template>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm --prefix frontend run test -- dashboard`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend
git commit -m "feat: add dashboard and management views"
```

### Task 6: Verify the Full MVP

**Files:**
- Modify: `backend/README.md`
- Modify: `frontend/README.md`
- Create: `README.md`

- [ ] **Step 1: Run backend verification**

Run: `python -m pytest backend/tests -q`
Expected: PASS

- [ ] **Step 2: Run frontend verification**

Run: `npm --prefix frontend run test`
Expected: PASS

- [ ] **Step 3: Run frontend build**

Run: `npm --prefix frontend run build`
Expected: PASS

- [ ] **Step 4: Run backend startup smoke test**

Run: `python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000`
Expected: Server starts without import errors.

- [ ] **Step 5: Commit**

```bash
git add .
git commit -m "docs: finalize livestock monitoring platform mvp"
```
