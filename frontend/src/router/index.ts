import type { RouteRecordRaw } from "vue-router";
import { createRouter, createWebHistory } from "vue-router";

import AppLayout from "../layouts/AppLayout.vue";
import AlertsView from "../views/AlertsView.vue";
import DashboardView from "../views/DashboardView.vue";
import DataAnalysisView from "../views/DataAnalysisView.vue";
import DataQueryView from "../views/DataQueryView.vue";
import DevicesView from "../views/DevicesView.vue";
import FarmsView from "../views/FarmsView.vue";
import InspectionsView from "../views/InspectionsView.vue";
import LoginView from "../views/LoginView.vue";
import ProtocolLogsView from "../views/ProtocolLogsView.vue";
import SensorsView from "../views/SensorsView.vue";
import TelemetryView from "../views/TelemetryView.vue";
import { useAuthStore } from "../stores/auth";

export const routes: RouteRecordRaw[] = [
  { path: "/login", component: LoginView },
  {
    path: "/",
    component: AppLayout,
    redirect: "/dashboard",
    children: [
      { path: "dashboard", component: DashboardView },
      { path: "farms", component: FarmsView },
      { path: "devices", component: DevicesView },
      { path: "sensors", component: SensorsView },
      { path: "telemetry", component: TelemetryView },
      { path: "data-query", component: DataQueryView },
      { path: "analysis", component: DataAnalysisView },
      { path: "protocol", component: ProtocolLogsView },
      { path: "alerts", component: AlertsView },
      { path: "inspections", component: InspectionsView }
    ]
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

router.beforeEach((to) => {
  const authStore = useAuthStore();
  if (to.path !== "/login" && !authStore.token) {
    return "/login";
  }
  if (to.path === "/login" && authStore.token) {
    return "/dashboard";
  }
  return true;
});

export default router;
