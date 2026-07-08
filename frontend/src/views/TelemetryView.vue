<template>
  <DataTableCard title="实时监测" description="展示数据库 telemetry_latest 中的最新遥测数据；PC/协议接收成功入库后会在这里更新。" :rows="displayRows" :columns="columns">
    <template #actions>
      <div class="page-actions">
        <span class="auto-refresh-text">每 30 秒自动刷新</span>
        <el-button type="primary" plain @click="void loadRows()">手动刷新</el-button>
      </div>
    </template>
    <template v-if="rows.length === 0">
      <el-table-column label="暂无实时数据" min-width="420">
        <template #default>
          <span class="empty-hint">暂无实时数据，请先通过 PC 端或协议接口上报数据。</span>
        </template>
      </el-table-column>
    </template>
  </DataTableCard>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";

import { fetchRows } from "../api/client";
import DataTableCard from "../components/common/DataTableCard.vue";
import { readableFactorName } from "../utils/factors";

const REFRESH_INTERVAL_MS = 30000;

const rows = ref<Record<string, unknown>[]>([]);
const columns = [
  { prop: "deviceId", label: "设备 ID" },
  { prop: "factorName", label: "因子名称" },
  { prop: "value", label: "数值" },
  { prop: "unit", label: "单位" },
  { prop: "qualityLabel", label: "质量" },
  { prop: "recordedAtBeijing", label: "采集时间（北京）", minWidth: 190 },
  { prop: "commandCode", label: "CN", minWidth: 80 }
];

const displayRows = computed(() =>
  rows.value.map((row) => ({
    ...row,
    factorName: readableFactorName(row),
    qualityLabel: readableQuality(row.quality)
  }))
);

let timer: number | null = null;

async function loadRows() {
  rows.value = await fetchRows("/telemetry/latest");
}

function readableQuality(value: unknown) {
  const quality = String(value ?? "");
  if (quality === "N" || quality === "good") {
    return "正常";
  }
  if (quality === "warning") {
    return "预警";
  }
  if (quality === "bad" || quality === "error") {
    return "异常";
  }
  return quality || "无";
}

onMounted(async () => {
  await loadRows();
  timer = window.setInterval(() => {
    void loadRows();
  }, REFRESH_INTERVAL_MS);
});

onUnmounted(() => {
  if (timer !== null) {
    window.clearInterval(timer);
  }
});
</script>
