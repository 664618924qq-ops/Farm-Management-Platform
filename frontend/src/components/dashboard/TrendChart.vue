<template>
  <div class="chart-card">
    <header class="section-header">
      <div>
        <h3>环境趋势</h3>
        <p>最近采样记录按指标分组展示。</p>
      </div>
    </header>
    <VChart class="chart" :option="option" autoresize />
  </div>
</template>

<script setup lang="ts">
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { GridComponent, LegendComponent, TooltipComponent } from "echarts/components";
import { LineChart } from "echarts/charts";
import VChart from "vue-echarts";
import { computed } from "vue";

use([CanvasRenderer, GridComponent, LegendComponent, TooltipComponent, LineChart]);

const props = defineProps<{
  series: Array<{ sensorCode: string; points: Array<{ time: string; value: number }> }>;
}>();

const option = computed(() => ({
  backgroundColor: "transparent",
  tooltip: { trigger: "axis" },
  legend: {
    textStyle: { color: "#35524a" }
  },
  grid: { left: 24, right: 24, top: 36, bottom: 24, containLabel: true },
  xAxis: {
    type: "category",
    boundaryGap: false,
    axisLabel: { color: "#5f766d" },
    data: props.series[0]?.points.map((item) => item.time.slice(11, 16)) ?? []
  },
  yAxis: {
    type: "value",
    axisLabel: { color: "#5f766d" },
    splitLine: { lineStyle: { color: "rgba(83, 120, 107, 0.12)" } }
  },
  series: props.series.map((item, index) => ({
    name: item.sensorCode,
    type: "line",
    smooth: true,
    showSymbol: false,
    lineStyle: { width: 3 },
    color: ["#1d7a64", "#2f9f95", "#d2744e", "#4d5cf0", "#b58d28"][index % 5],
    data: item.points.map((point) => point.value)
  }))
}));
</script>
