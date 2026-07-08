<template>
  <section class="table-card">
    <header class="section-header">
      <div>
        <h2>{{ title }}</h2>
        <p>{{ description }}</p>
      </div>
      <slot name="actions" />
    </header>
    <el-table :data="rows" style="width: 100%">
      <el-table-column
        v-for="column in columns"
        :key="column.prop"
        :prop="column.prop"
        :label="column.label"
        :min-width="column.minWidth ?? 120"
      />
      <slot />
    </el-table>
  </section>
</template>

<script setup lang="ts">
defineProps<{
  title: string;
  description: string;
  rows: Record<string, unknown>[];
  columns: Array<{ prop: string; label: string; minWidth?: number }>;
}>();
</script>
