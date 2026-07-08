<template>
  <section class="dashboard-page">
    <header class="hero-panel">
      <div>
        <span class="hero-tag">平台总览</span>
        <h1>养殖场监测总览</h1>
        <p>集中查看平台接收、实时数据、设备在线和告警状态。总览信息会自动更新，也可以点击按钮立即同步。</p>
        <div class="page-actions dashboard-actions">
          <span class="auto-refresh-text">总览与联调状态每 10 秒自动更新</span>
          <el-button type="primary" plain @click="void store.load()">立即同步</el-button>
        </div>
      </div>
      <div class="hero-grid">
        <MetricCard label="养殖场数量" :value="store.summary.farmCount" hint="已纳入平台管理" />
        <MetricCard label="棚舍数量" :value="store.summary.shedCount" hint="已覆盖监测区域" />
        <MetricCard label="在线设备" :value="store.summary.onlineDeviceCount" hint="当前活跃网关" />
        <MetricCard label="活动告警" :value="store.summary.activeAlertCount" hint="需要关注处理" />
      </div>
    </header>

    <section class="table-card integration-card">
      <header class="section-header">
        <div>
          <h2>联调状态看板</h2>
          <p>验收时优先查看这里：确认平台已收到 PC 报文、已入库并返回合法 CN=9014 ACK。</p>
        </div>
      </header>
      <div class="integration-grid">
        <article class="integration-item">
          <span class="integration-label">最近报文时间</span>
          <strong>{{ store.summary.integrationStatus.lastPacketTime ?? "暂无数据" }}</strong>
        </article>
        <article class="integration-item">
          <span class="integration-label">最近设备 MN</span>
          <strong>{{ store.summary.integrationStatus.lastDevice ?? "暂无数据" }}</strong>
        </article>
        <article class="integration-item">
          <span class="integration-label">最近接收状态</span>
          <strong>{{ readableReceiveStatus }}</strong>
        </article>
        <article class="integration-item">
          <span class="integration-label">ACK 状态</span>
          <strong>{{ readableAckStatus }}</strong>
        </article>
        <article class="integration-item integration-item-wide">
          <span class="integration-label">最近接收结果</span>
          <strong>{{ readableReceiveResult }}</strong>
          <span class="integration-hint">
            命令 {{ store.summary.integrationStatus.lastCommand ?? "-" }} /
            指标数 {{ store.summary.integrationStatus.lastMetricCount }}
          </span>
        </article>
        <article class="integration-item integration-item-wide">
          <span class="integration-label">ACK 包摘要</span>
          <strong>{{ readableAckSummary }}</strong>
        </article>
      </div>
    </section>

    <TrendChart :series="store.trends" />
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted } from "vue";

import MetricCard from "../components/dashboard/MetricCard.vue";
import TrendChart from "../components/dashboard/TrendChart.vue";
import { useDashboardStore } from "../stores/dashboard";

const store = useDashboardStore();
let timer: number | null = null;

const RECEIVE_STATUS_LABELS: Record<string, string> = {
  accepted: "接收成功",
  rejected: "解析失败",
  ingest_failed: "入库失败"
};

const RECEIVE_RESULT_LABELS: Record<string, string> = {
  "TCP accepted and stored": "TCP 已接收并入库",
  "HTTP accepted and stored": "HTTP 已接收并入库",
  "TCP received but parse rejected": "TCP 已接收但解析失败",
  "HTTP received but parse rejected": "HTTP 已接收但解析失败",
  "TCP parsed but ingest failed": "TCP 已解析但入库失败",
  "HTTP parsed but ingest failed": "HTTP 已解析但入库失败"
};

const ACK_STATUS_LABELS: Record<string, string> = {
  valid_9014_ack: "ACK 正常（已返回 CN=9014）",
  missing_ack: "未记录到 ACK",
  not_applicable: "未生成成功 ACK"
};

const ACK_SUMMARY_LABELS: Record<string, string> = {
  "CN=9014 ACK returned": "平台已返回 CN=9014 ACK",
  "Accepted but ACK not recorded": "数据已接收，但未记录到 ACK",
  "No success ACK for this packet": "本次报文未生成成功 ACK"
};

const readableReceiveStatus = computed(() => {
  const rawStatus = store.summary.integrationStatus.lastStatus;
  return rawStatus ? RECEIVE_STATUS_LABELS[rawStatus] ?? rawStatus : "暂无数据";
});

const readableReceiveResult = computed(() => {
  const rawResult = store.summary.integrationStatus.lastReceiveResult;
  return rawResult ? RECEIVE_RESULT_LABELS[rawResult] ?? rawResult : "暂无数据";
});

const readableAckStatus = computed(() => {
  const rawStatus = store.summary.integrationStatus.lastAckStatus;
  return rawStatus ? ACK_STATUS_LABELS[rawStatus] ?? rawStatus : "暂无数据";
});

const readableAckSummary = computed(() => {
  const rawSummary = store.summary.integrationStatus.lastAckSummary;
  return rawSummary ? ACK_SUMMARY_LABELS[rawSummary] ?? rawSummary : "暂无数据";
});

onMounted(() => {
  void store.load();
  timer = window.setInterval(() => {
    void store.load();
  }, 10000);
});

onUnmounted(() => {
  if (timer !== null) {
    window.clearInterval(timer);
  }
});
</script>
