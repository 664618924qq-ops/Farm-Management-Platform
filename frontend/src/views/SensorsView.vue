<template>
  <DataTableCard :title="i18nStore.t('sensors.title')" :description="i18nStore.t('sensors.description')" :rows="rows" :columns="columns" />
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { fetchRows } from "../api/client";
import DataTableCard from "../components/common/DataTableCard.vue";
import { useI18nStore } from "../stores/i18n";

const rows = ref<Record<string, unknown>[]>([]);
const i18nStore = useI18nStore();
const columns = computed(() => [
  { prop: "code", label: i18nStore.t("sensors.code") },
  { prop: "name", label: i18nStore.t("sensors.name") },
  { prop: "unit", label: i18nStore.t("sensors.unit") },
  { prop: "lowerLimit", label: i18nStore.t("sensors.low") },
  { prop: "upperLimit", label: i18nStore.t("sensors.high") }
]);

onMounted(async () => {
  rows.value = await fetchRows("/sensors");
});
</script>
