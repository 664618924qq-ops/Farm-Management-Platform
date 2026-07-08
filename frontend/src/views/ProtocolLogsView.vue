<template>
  <section class="table-card">
    <header class="section-header">
      <div>
        <h2>协议接收日志</h2>
        <p>默认不自动刷新，按条件手动查询数据库日志；DataTime、平台接收时间、入库时间均按北京时间展示。</p>
      </div>
      <div class="page-actions">
        <el-button type="primary" plain @click="void loadRows()">手动查询</el-button>
      </div>
    </header>

    <div class="query-form protocol-log-query">
      <label>设备 MN <input v-model="filters.mn" placeholder="A110000_0001" /></label>
      <label>命令 CN（多选，空为全部）
        <el-select v-model="filters.cn" multiple collapse-tags collapse-tags-tooltip placeholder="全部 CN" class="cn-select">
          <el-option v-for="item in cnOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
      </label>
      <label>状态
        <select v-model="filters.status">
          <option value="">全部</option>
          <option value="accepted">接收成功</option>
          <option value="rejected">解析失败</option>
          <option value="ingest_failed">入库失败</option>
        </select>
      </label>
      <label>开始时间（北京时间） <input v-model="filters.startTime" type="datetime-local" /></label>
      <label>结束时间（北京时间） <input v-model="filters.endTime" type="datetime-local" /></label>
    </div>
    <p class="time-note">
      默认时间范围为今天 00:00:00 到当前时间。HJ212 DataTime 为设备采集/监测时间；平台接收时间为 TCP/HTTP 收到报文时间；入库时间当前与接收日志落库时间一致。
    </p>

    <el-table :data="rows" style="width: 100%">
      <el-table-column type="expand">
        <template #default="{ row }">
          <div class="packet-detail">
            <strong>原始报文</strong>
            <pre>{{ row.rawPacket }}</pre>
            <strong>平台应答</strong>
            <pre>{{ row.ackPacket || "暂无应答" }}</pre>
            <strong>错误原因</strong>
            <pre>{{ row.errorMessage || "无" }}</pre>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="来源" min-width="110">
        <template #default="{ row }">{{ readableSource(row.source) }}</template>
      </el-table-column>
      <el-table-column prop="mn" label="设备 MN" min-width="150" />
      <el-table-column prop="cn" label="命令 CN" min-width="90" />
      <el-table-column prop="qn" label="请求 QN" min-width="170" />
      <el-table-column prop="dataTimeBeijing" label="DataTime（北京）" min-width="210" />
      <el-table-column label="状态" min-width="120">
        <template #default="{ row }">
          <el-tag :type="statusTagType(row.status)">{{ readableStatus(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="metricCount" label="指标数" min-width="90" />
      <el-table-column prop="receivedAtBeijing" label="平台接收时间（北京）" min-width="220" />
      <el-table-column prop="storedAtBeijing" label="入库时间（北京）" min-width="220" />
    </el-table>
  </section>
</template>

<script setup lang="ts">
import { reactive, ref } from "vue";

import { fetchProtocolLogs, type ProtocolLog } from "../api/client";

const rows = ref<ProtocolLog[]>([]);
const cnOptions = [
  { label: "2011 实时数据", value: "2011" },
  { label: "2061 小时数据", value: "2061" },
  { label: "9014 应答/ACK", value: "9014" }
];
const filters = reactive({
  mn: "",
  cn: [] as string[],
  status: "",
  startTime: formatDateTimeLocal(startOfToday()),
  endTime: formatDateTimeLocal(new Date())
});

async function loadRows() {
  rows.value = await fetchProtocolLogs({
    mn: filters.mn || undefined,
    cn: filters.cn.length > 0 ? filters.cn.join(",") : undefined,
    status: filters.status || undefined,
    startTime: filters.startTime || undefined,
    endTime: filters.endTime || undefined
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

function statusTagType(status: string) {
  if (status === "accepted") return "success";
  if (status === "rejected") return "warning";
  if (status === "ingest_failed") return "danger";
  return "info";
}

function readableSource(source: string) {
  if (source === "tcp") return "TCP 接收";
  if (source === "http") return "HTTP 上传";
  return source;
}

function readableStatus(status: string) {
  if (status === "accepted") return "接收成功";
  if (status === "rejected") return "解析失败";
  if (status === "ingest_failed") return "入库失败";
  return status;
}
</script>
