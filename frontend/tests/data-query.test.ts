import { fireEvent, render, screen, waitFor } from "@testing-library/vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

import DataQueryView from "../src/views/DataQueryView.vue";
import { fetchDataQuery } from "../src/api/client";

vi.mock("../src/api/client", () => ({
  fetchDataQuery: vi.fn()
}));

const fetchDataQueryMock = vi.mocked(fetchDataQuery);

const elSelectStub = {
  props: ["modelValue", "multiple", "placeholder"],
  emits: ["update:modelValue"],
  template: `
    <div>
      <button type="button" @click="$emit('update:modelValue', ['w01010', 'w01014'])">选择水温和 pH</button>
      <slot />
    </div>
  `
};

const elOptionStub = {
  props: ["label", "value"],
  template: "<span>{{ label }}</span>"
};

const elTableStub = {
  props: ["data"],
  template: `
    <table>
      <thead><tr><slot /></tr></thead>
      <tbody>
        <tr v-for="row in data" :key="row.id">
          <td>{{ row.recordedAtBeijing }}</td>
          <td>{{ row.mn }}</td>
          <td>{{ row.factorName }}</td>
          <td>{{ row.value }}</td>
          <td>{{ row.unit }}</td>
          <td>{{ row.qualityLabel }}</td>
        </tr>
      </tbody>
    </table>
  `
};

const elTableColumnStub = {
  props: ["label"],
  template: "<th>{{ label }}</th>"
};

describe("DataQueryView", () => {
  beforeEach(() => {
    fetchDataQueryMock.mockReset();
    fetchDataQueryMock.mockResolvedValue({
      cn: "2011",
      mode: "实时数据查询",
      timeSemantics: "采集时刻",
      timezone: "Asia/Shanghai",
      dataSource: "database",
      items: [
        {
          id: 1,
          mn: "A110000_0001",
          sensorCode: "w01010",
          sensorName: "Temperature",
          value: 28.6,
          unit: "℃",
          recordedAtBeijing: "2026-07-07T12:49:34+08:00",
          qualityLabel: "正常"
        }
      ]
    });
  });

  it("shows factor names instead of sensor codes and submits multi-selected codes internally", async () => {
    render(DataQueryView, {
      global: {
        stubs: {
          "el-button": { template: '<button @click="$emit(\'click\')"><slot /></button>' },
          "el-select": elSelectStub,
          "el-option": elOptionStub,
          "el-table": elTableStub,
          "el-table-column": elTableColumnStub
        }
      }
    });

    expect(screen.getByText("因子名称")).toBeTruthy();
    expect(screen.queryByText("指标编码")).toBeNull();
    expect(screen.queryByPlaceholderText("w01010")).toBeNull();

    await fireEvent.click(screen.getByText("选择水温和 pH"));
    await fireEvent.click(screen.getByText("手动查询"));

    await waitFor(() => {
      expect(fetchDataQueryMock).toHaveBeenCalledWith(
        expect.objectContaining({
          sensorCode: "w01010,w01014"
        })
      );
    });

    await waitFor(() => {
      expect(screen.getAllByText("水温").length).toBeGreaterThanOrEqual(2);
    });
    expect(screen.queryByText("w01010")).toBeNull();
  });
});
