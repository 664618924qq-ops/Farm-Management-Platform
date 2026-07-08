<template>
  <section class="dashboard-page">
    <section class="table-card">
      <header class="section-header">
        <div>
          <h2>数据分析</h2>
          <p>基于数据库历史遥测记录分析趋势、质量标记和处理建议；结论仅作为现场复核参考。</p>
        </div>
        <div class="page-actions">
          <el-button type="primary" plain @click="void loadAnalysis()">手动分析</el-button>
        </div>
      </header>

      <div class="query-form">
        <label>数据类型
          <select v-model="filters.cn">
            <option value="2011">实时数据 CN=2011</option>
            <option value="2061">小时数据 CN=2061</option>
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
        <label>开始时间（北京时间）<input v-model="filters.startTime" type="datetime-local" /></label>
        <label>结束时间（北京时间）<input v-model="filters.endTime" type="datetime-local" /></label>
      </div>

      <p class="time-note">数据来源：{{ analysis?.dataSource === "database" ? "数据库历史遥测记录" : "等待查询" }}；展示/查询时区：北京时间 Asia/Shanghai；空因子条件表示分析全部因子。</p>

      <div class="analysis-summary">
        <article><span>记录数</span><strong>{{ analysis?.summary.recordCount ?? 0 }}</strong></article>
        <article><span>指标数</span><strong>{{ analysis?.summary.sensorCount ?? 0 }}</strong></article>
        <article><span>质量提示</span><strong>{{ analysis?.summary.findingCount ?? 0 }}</strong></article>
      </div>
    </section>

    <section class="table-card">
      <h3>趋势摘要</h3>
      <el-table :data="seriesRows" style="width: 100%">
        <el-table-column prop="factorName" label="因子名称" min-width="140" />
        <el-table-column prop="min" label="最小值" />
        <el-table-column prop="avg" label="平均值" />
        <el-table-column prop="max" label="最大值" />
        <el-table-column label="点数" min-width="80">
          <template #default="{ row }">{{ row.points?.length ?? 0 }}</template>
        </el-table-column>
        <el-table-column prop="basis" label="阈值依据/说明" min-width="380" />
      </el-table>
    </section>

    <section class="table-card">
      <h3>异常与建议</h3>
      <el-table :data="findingRows" style="width: 100%">
        <el-table-column prop="factorName" label="因子名称" min-width="140" />
        <el-table-column prop="qualityLabel" label="质量标记" min-width="120" />
        <el-table-column prop="latestValue" label="当前值" min-width="100" />
        <el-table-column prop="message" label="解释/建议" min-width="360" />
        <el-table-column prop="basis" label="依据" min-width="380" />
      </el-table>
      <ul class="suggestion-list">
        <li v-for="item in analysis?.suggestions ?? []" :key="item">{{ item }}</li>
      </ul>
    </section>

    <section class="table-card">
      <h3>短信通知预留</h3>
      <p class="time-note">当前仅保留短信抽象和测试日志，不绑定服务商、不写入密钥、不产生资费。</p>
      <div class="query-form">
        <label>手机号 <input v-model="smsPhone" placeholder="13800000000" /></label>
        <label>模板 <input v-model="smsTemplate" placeholder="quality_alert" /></label>
        <el-button plain @click="void testSms()">测试发送（仅 dry-run）</el-button>
      </div>
      <p class="time-note">{{ smsResult }}</p>
    </section>
  </section>
</template>

<script setup lang="ts">
import axios from "axios";
import { computed, onMounted, reactive, ref } from "vue";

import { fetchAnalysis, type AnalysisResponse } from "../api/client";
import { factorOptions, readableFactorName } from "../utils/factors";

const filters = reactive({
  cn: "2011",
  mn: "",
  sensorCodes: [] as string[],
  startTime: formatDateTimeLocal(startOfToday()),
  endTime: formatDateTimeLocal(new Date())
});
const analysis = ref<AnalysisResponse | null>(null);
const smsPhone = ref("");
const smsTemplate = ref("quality_alert");
const smsResult = ref("");
const seriesRows = computed(() =>
  (analysis.value?.series ?? []).map((item) => ({
    ...item,
    factorName: readableFactorName(item)
  }))
);
const findingRows = computed(() =>
  (analysis.value?.findings ?? []).map((item) => ({
    ...item,
    factorName: readableFactorName(item)
  }))
);

async function loadAnalysis() {
  analysis.value = await fetchAnalysis({
    cn: filters.cn,
    mn: filters.mn || undefined,
    sensorCode: filters.sensorCodes.length > 0 ? filters.sensorCodes.join(",") : undefined,
    startTime: filters.startTime || undefined,
    endTime: filters.endTime || undefined,
    limit: 300
  });
}

async function testSms() {
  const response = await axios.post("http://127.0.0.1:8000/api/v1/notifications/sms-test", {
    phoneNumber: smsPhone.value || "13800000000",
    templateCode: smsTemplate.value,
    content: "平台短信通知预留测试"
  });
  smsResult.value = `${response.data.status}: ${response.data.message}`;
}

onMounted(() => {
  void loadAnalysis();
});

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
