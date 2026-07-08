<template>
  <section class="table-card">
    <header class="section-header">
      <div>
        <h2>数据查询</h2>
        <p>基于数据库历史记录查询，不依赖内存；CN=2011 按实时采集时刻，CN=2061 按小时监测时段理解。</p>
      </div>
      <div class="page-actions">
        <el-button type="primary" plain @click="void loadRows()">手动查询</el-button>
      </div>
    </header>

    <div class="query-form">
      <label>数据类型
        <select v-model="filters.cn">
          <option value="2011">实时数据查询 CN=2011</option>
          <option value="2061">小时数据查询 CN=2061</option>
        </select>
      </label>
      <label>设备 MN <input v-model="filters.mn" placeholder="A110000_0001" /></label>
      <label>因子名称（多选，空为全部）
        <el-select
          v-model="filters.sensorCodes"
          multiple
          collapse-tags
          collapse-tags-tooltip
          placeholder="全部因子"
          class="factor-select"
        >
          <el-option v-for="item in factorOptions" :key="item.code" :label="item.name" :value="item.code" />
        </el-select>
      </label>
      <label>开始时间（北京时间） <input v-model="filters.startTime" type="datetime-local" /></label>
      <label>结束时间（北京时间） <input v-model="filters.endTime" type="datetime-local" /></label>
    </div>

    <p class="time-note">
      默认时间范围为今天 00:00:00 到当前时间。当前口径：{{ result?.mode ?? "-" }}；时间语义：{{ result?.timeSemantics ?? "-" }}；数据来源：数据库历史遥测记录；展示和查询时区：北京时间 Asia/Shanghai。
    </p>
    <p v-if="showEmptyHint" class="empty-hint">
      当前条件下未查询到数据，请检查数据类型、设备 MN、因子名称或北京时间范围
    </p>

    <el-table :data="rows" style="width: 100%">
      <el-table-column prop="recordedAtBeijing" label="采集/统计时间（北京）" min-width="210" />
      <el-table-column prop="mn" label="设备 MN" min-width="150" />
      <el-table-column prop="factorName" label="因子名称" min-width="140" />
      <el-table-column prop="value" label="数值" min-width="90" />
      <el-table-column prop="unit" label="单位" min-width="80" />
      <el-table-column prop="qualityLabel" label="质量标记" min-width="120" />
      <el-table-column prop="qualityMessage" label="解释/建议" min-width="300" />
      <el-table-column prop="qualityBasis" label="依据" min-width="360" />
    </el-table>
  </section>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from "vue";

import { fetchDataQuery, type DataQueryResponse } from "../api/client";
import { factorOptions, readableFactorName } from "../utils/factors";

const filters = reactive({
  cn: "2011",
  mn: "",
  sensorCodes: [] as string[],
  startTime: formatDateTimeLocal(startOfToday()),
  endTime: formatDateTimeLocal(new Date())
});
const result = ref<DataQueryResponse | null>(null);
const rows = computed(() =>
  (result.value?.items ?? []).map((item) => ({
    ...item,
    factorName: readableFactorName(item)
  }))
);
const showEmptyHint = computed(() => result.value !== null && rows.value.length === 0);

async function loadRows() {
  result.value = await fetchDataQuery({
    cn: filters.cn,
    mn: filters.mn || undefined,
    sensorCode: filters.sensorCodes.length > 0 ? filters.sensorCodes.join(",") : undefined,
    startTime: filters.startTime || undefined,
    endTime: filters.endTime || undefined,
    limit: 300
  });
}

function startOfToday() {
  const value = new Date();
  value.setHours(0, 0, 0, 0);
  return value;
}

function formatDateTimeLocal(value: Date) {
  const pad = (input: number) => String(input).padStart(2, "0");
  return `${value.getFullYear()}-${pad(value.getMonth() + 1)}-${pad(value.getDate())}T${pad(value.getHours())}:${pad(value.getMinutes())}:${pad(value.getSeconds())}`;
}

</script>
