import { render, screen, waitFor } from "@testing-library/vue";
import { describe, expect, it, vi } from "vitest";

import AlertsView from "../src/views/AlertsView.vue";
import DataAnalysisView from "../src/views/DataAnalysisView.vue";
import DataQueryView from "../src/views/DataQueryView.vue";
import TelemetryView from "../src/views/TelemetryView.vue";
import { fetchAnalysis, fetchDataQuery, fetchRows } from "../src/api/client";

vi.mock("../src/api/client", () => ({
  acknowledgeAlert: vi.fn(),
  fetchAnalysis: vi.fn(),
  fetchDataQuery: vi.fn(),
  fetchRows: vi.fn()
}));

const fetchRowsMock = vi.mocked(fetchRows);
const fetchAnalysisMock = vi.mocked(fetchAnalysis);
const fetchDataQueryMock = vi.mocked(fetchDataQuery);

const dataTableCardStub = {
  props: ["title", "description", "rows", "columns"],
  template: `
    <section>
      <h2>{{ title }}</h2>
      <p>{{ description }}</p>
      <table>
        <thead>
          <tr>
            <th v-for="column in columns" :key="column.prop">{{ column.label }}</th>
            <slot />
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.id">
            <td v-for="column in columns" :key="column.prop">{{ row[column.prop] }}</td>
          </tr>
        </tbody>
      </table>
    </section>
  `
};

const elTableStub = {
  props: ["data"],
  template: `
    <table>
      <thead><tr><slot /></tr></thead>
      <tbody>
        <tr v-for="row in data" :key="row.id ?? row.sensorName">
          <td>{{ row.factorName }}</td>
          <td>{{ row.min }}</td>
          <td>{{ row.avg }}</td>
          <td>{{ row.max }}</td>
          <td>{{ row.qualityLabel }}</td>
          <td>{{ row.latestValue }}</td>
        </tr>
      </tbody>
    </table>
  `
};

const elTableColumnStub = {
  props: ["label"],
  template: "<th>{{ label }}</th>"
};

describe("technical fields are translated on user-facing pages", () => {
  it("shows factor names on realtime monitoring instead of sensor code columns", async () => {
    fetchRowsMock.mockResolvedValueOnce([
      {
        id: 1,
        deviceId: 1,
        sensorCode: "w01010",
        sensorName: "Temperature",
        value: 28.6,
        unit: "℃",
        quality: "N",
        recordedAtBeijing: "2026-07-07T12:49:34+08:00"
      }
    ]);

    render(TelemetryView, {
      global: {
        stubs: {
          DataTableCard: dataTableCardStub,
          "el-button": { template: "<button><slot /></button>" },
          "el-table-column": elTableColumnStub
        }
      }
    });

    await waitFor(() => expect(screen.getByText("水温")).toBeTruthy());
    expect(screen.getAllByText("因子名称").length).toBeGreaterThan(0);
    expect(screen.queryByText("指标编码")).toBeNull();
    expect(screen.queryByText("w01010")).toBeNull();
  });

  it("shows factor names on data analysis filters and tables", async () => {
    fetchAnalysisMock.mockResolvedValueOnce({
      cn: "2011",
      timezone: "Asia/Shanghai",
      dataSource: "database",
      summary: { recordCount: 1, sensorCount: 1, findingCount: 1 },
      series: [
        {
          sensorCode: "w01010",
          sensorName: "Temperature",
          unit: "℃",
          min: 28,
          avg: 28.6,
          max: 29,
          points: [],
          threshold: null,
          basis: "可配置阈值"
        }
      ],
      findings: [
        {
          sensorCode: "w01010",
          sensorName: "Temperature",
          latestValue: 29,
          qualityLabel: "正常"
        }
      ],
      suggestions: []
    });

    render(DataAnalysisView, {
      global: {
        stubs: {
          "el-button": { template: "<button><slot /></button>" },
          "el-select": { template: "<div><slot /></div>" },
          "el-option": { props: ["label"], template: "<span>{{ label }}</span>" },
          "el-table": elTableStub,
          "el-table-column": elTableColumnStub
        }
      }
    });

    await waitFor(() => expect(screen.getAllByText("水温").length).toBeGreaterThan(0));
    expect(screen.getAllByText("因子名称").length).toBeGreaterThan(0);
    expect(screen.queryByText("指标编码")).toBeNull();
    expect(screen.queryByPlaceholderText("w01010")).toBeNull();
    expect(screen.queryByText("w01010")).toBeNull();
  });

  it("shows factor names on alert center instead of factor codes", async () => {
    fetchRowsMock.mockResolvedValueOnce([
      {
        id: 1,
        levelLabel: "预警",
        deviceCode: "A110000_0001",
        sensorCode: "w01010",
        reason: "水温超过参考范围",
        suggestion: "建议现场复核",
        triggeredAtBeijing: "2026-07-07T12:49:34+08:00",
        status: "active",
        statusLabel: "待处理"
      }
    ]);

    render(AlertsView, {
      global: {
        stubs: {
          DataTableCard: dataTableCardStub,
          "el-table-column": elTableColumnStub,
          "el-button": { template: "<button><slot /></button>" }
        }
      }
    });

    await waitFor(() => expect(screen.getByText("水温")).toBeTruthy());
    expect(screen.getByText("因子名称")).toBeTruthy();
    expect(screen.queryByText("因子编码")).toBeNull();
    expect(screen.queryByText("w01010")).toBeNull();
  });

  it("shows a clear empty hint when data query returns no rows", async () => {
    fetchDataQueryMock.mockResolvedValueOnce({
      cn: "2011",
      mode: "实时数据查询",
      timeSemantics: "采集时刻",
      timezone: "Asia/Shanghai",
      dataSource: "database",
      items: []
    });

    render(DataQueryView, {
      global: {
        stubs: {
          "el-button": { template: '<button @click="$emit(\'click\')"><slot /></button>' },
          "el-select": { template: "<div><slot /></div>" },
          "el-option": { props: ["label"], template: "<span>{{ label }}</span>" },
          "el-table": elTableStub,
          "el-table-column": elTableColumnStub
        }
      }
    });

    await screen.findByText("手动查询").then((button) => button.click());
    await waitFor(() => {
      expect(screen.getByText("当前条件下未查询到数据，请检查数据类型、设备 MN、因子名称或北京时间范围")).toBeTruthy();
    });
  });
});
