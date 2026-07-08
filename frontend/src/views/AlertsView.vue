<template>
  <DataTableCard title="告警中心" description="展示设备、因子、触发原因、处理建议、时间和处理状态，便于验收现场快速判断风险。" :rows="rows" :columns="columns">
    <el-table-column label="操作" :min-width="120">
      <template #default="scope">
        <el-button type="primary" plain size="small" :disabled="scope?.row?.status !== 'active'" @click="handleAcknowledge(scope?.row?.id as number)">
          确认处理
        </el-button>
      </template>
    </el-table-column>
  </DataTableCard>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { acknowledgeAlert, fetchRows } from "../api/client";
import DataTableCard from "../components/common/DataTableCard.vue";
import { readableFactorName } from "../utils/factors";

const rawRows = ref<Record<string, unknown>[]>([]);
const rows = computed(() =>
  rawRows.value.map((row) => ({
    ...row,
    factorName: readableFactorName(row)
  }))
);
const columns = [
  { prop: "levelLabel", label: "告警等级", minWidth: 100 },
  { prop: "deviceCode", label: "设备/MN", minWidth: 140 },
  { prop: "factorName", label: "因子名称", minWidth: 120 },
  { prop: "reason", label: "触发原因", minWidth: 260 },
  { prop: "suggestion", label: "处理建议", minWidth: 280 },
  { prop: "triggeredAtBeijing", label: "触发时间（北京）", minWidth: 210 },
  { prop: "statusLabel", label: "状态", minWidth: 100 }
];

async function loadRows() {
  rawRows.value = await fetchRows("/alerts");
}

async function handleAcknowledge(alertId: number) {
  await acknowledgeAlert(alertId);
  await loadRows();
}

onMounted(loadRows);
</script>
