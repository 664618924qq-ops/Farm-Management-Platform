import { defineStore } from "pinia";

import { fetchDashboardSummary, fetchDashboardTrends, type DashboardSummary, type TrendSeries } from "../api/client";

type DashboardState = {
  summary: DashboardSummary;
  trends: TrendSeries[];
  loading: boolean;
};

export const useDashboardStore = defineStore("dashboard", {
  state: (): DashboardState => ({
    summary: {
      farmCount: 0,
      shedCount: 0,
      onlineDeviceCount: 0,
      activeAlertCount: 0,
      integrationStatus: {
        lastPacketTime: null,
        lastDevice: null,
        lastStatus: null,
        lastReceiveResult: null,
        lastCommand: null,
        lastMetricCount: 0,
        lastAckStatus: null,
        lastAckSummary: null
      }
    },
    trends: [],
    loading: false
  }),
  actions: {
    async load() {
      this.loading = true;
      try {
        const [summary, trends] = await Promise.all([fetchDashboardSummary(), fetchDashboardTrends()]);
        this.summary = summary;
        this.trends = trends;
      } finally {
        this.loading = false;
      }
    }
  }
});
