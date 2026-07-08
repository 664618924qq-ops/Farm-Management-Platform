<template>
  <article class="metric-card">
    <span class="metric-label">{{ label }}</span>
    <strong class="metric-value">{{ value }}</strong>
    <span class="metric-hint">{{ hint }}</span>
  </article>
</template>

<script setup lang="ts">
defineProps<{
  label: string;
  value: string | number;
  hint: string;
}>();
</script>
