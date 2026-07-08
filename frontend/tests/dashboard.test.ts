import { render, screen } from "@testing-library/vue";
import { createPinia } from "pinia";
import { reactive } from "vue";
import { vi } from "vitest";

import DashboardView from "../src/views/DashboardView.vue";

vi.mock("../src/stores/dashboard", () => ({
  useDashboardStore: () =>
    reactive({
      summary: {
        farmCount: 2,
        shedCount: 3,
        onlineDeviceCount: 2,
        activeAlertCount: 1,
        integrationStatus: {
          lastPacketTime: "2026-07-06T10:35:00+08:00",
          lastDevice: "A110000_0001",
          lastStatus: "accepted",
          lastReceiveResult: "TCP accepted and stored",
          lastCommand: "2011",
          lastMetricCount: 5,
          lastAckStatus: "valid_9014_ack",
          lastAckSummary: "CN=9014 ACK returned"
        }
      },
      trends: [],
      load: vi.fn()
    })
}));

test("shows dashboard title, sync button, and readable integration evidence", () => {
  render(DashboardView, {
    global: {
      plugins: [createPinia()],
      stubs: {
        TrendChart: true,
        "el-button": { template: "<button><slot /></button>" }
      }
    }
  });

  expect(screen.getByText("养殖场监测总览")).toBeTruthy();
  expect(screen.getByText("立即同步")).toBeTruthy();
  expect(screen.getByText("最近接收状态")).toBeTruthy();
  expect(screen.getByText("接收成功")).toBeTruthy();
  expect(screen.getByText("TCP 已接收并入库")).toBeTruthy();
  expect(screen.getByText("ACK 状态")).toBeTruthy();
  expect(screen.getByText("ACK 正常（已返回 CN=9014）")).toBeTruthy();
  expect(screen.getByText("平台已返回 CN=9014 ACK")).toBeTruthy();
});
