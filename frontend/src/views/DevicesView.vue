<template>
  <DataTableCard :title="i18nStore.t('devices.title')" :description="i18nStore.t('devices.description')" :rows="rows" :columns="columns" />
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { fetchRows } from "../api/client";
import DataTableCard from "../components/common/DataTableCard.vue";
import { useI18nStore } from "../stores/i18n";

const rows = ref<Record<string, unknown>[]>([]);
const i18nStore = useI18nStore();
const columns = computed(() => [
  { prop: "code", label: i18nStore.t("devices.code") },
  { prop: "name", label: i18nStore.t("devices.name") },
  { prop: "deviceType", label: i18nStore.t("devices.type") },
  { prop: "protocolType", label: i18nStore.t("devices.protocol") },
  { prop: "status", label: i18nStore.t("devices.status") }
]);

onMounted(async () => {
  rows.value = await fetchRows("/devices");
});
</script>
