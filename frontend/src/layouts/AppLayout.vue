<template>
  <div class="app-shell">
    <aside class="sidebar">
      <div class="brand-block">
        <span class="brand-kicker">Livestock Monitor</span>
        <h1>养殖场监测平台</h1>
        <p>PC 采集端、平台接收端与 Web 管理端联调验收入口。</p>
      </div>
      <nav class="nav-links">
        <RouterLink v-for="item in navItems" :key="item.path" :to="item.path" class="nav-link">
          {{ item.label }}
        </RouterLink>
      </nav>
    </aside>
    <main class="main-panel">
      <header class="topbar">
        <div>
          <span class="topbar-label">当前页面</span>
          <strong>{{ currentLabel }}</strong>
        </div>
        <div class="topbar-actions">
          <span class="language-label">语言</span>
          <el-button-group>
            <el-button type="primary">中文</el-button>
            <el-button disabled>EN</el-button>
          </el-button-group>
          <div class="topbar-badge">
            {{ authStore.user?.role === "admin" ? "管理员视图" : "巡检视图" }}
          </div>
        </div>
      </header>
      <section class="page-content">
        <RouterView />
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";

import { useAuthStore } from "../stores/auth";

const route = useRoute();
const authStore = useAuthStore();
const navItems = [
  { path: "/dashboard", label: "总览" },
  { path: "/farms", label: "养殖场" },
  { path: "/devices", label: "设备管理" },
  { path: "/sensors", label: "传感器" },
  { path: "/telemetry", label: "实时监测" },
  { path: "/data-query", label: "数据查询" },
  { path: "/analysis", label: "数据分析" },
  { path: "/protocol", label: "协议接收日志" },
  { path: "/alerts", label: "告警中心" },
  { path: "/inspections", label: "巡检记录" }
];
const currentLabel = computed(() => navItems.find((item) => route.path.startsWith(item.path))?.label ?? "平台页面");
</script>
