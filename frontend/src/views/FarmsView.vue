<template>
  <DataTableCard :title="i18nStore.t('farms.title')" :description="i18nStore.t('farms.description')" :rows="rows" :columns="columns">
    <template #actions>
      <el-button type="primary" @click="openCreateDialog">{{ i18nStore.t("farms.add") }}</el-button>
    </template>
    <el-table-column :label="i18nStore.t('farms.actions')" :min-width="160">
      <template #default="{ row }">
        <el-button link type="primary" @click="openEditDialog(row)">{{ i18nStore.t("farms.edit") }}</el-button>
      </template>
    </el-table-column>
  </DataTableCard>

  <el-dialog v-model="dialogVisible" :title="editingId ? i18nStore.t('farms.editTitle') : i18nStore.t('farms.createTitle')" width="520px">
    <el-form :model="form" label-width="120px">
      <el-form-item :label="i18nStore.t('farms.code')"><el-input v-model="form.code" /></el-form-item>
      <el-form-item :label="i18nStore.t('farms.name')"><el-input v-model="form.name" /></el-form-item>
      <el-form-item :label="i18nStore.t('farms.contact')"><el-input v-model="form.contact_name" /></el-form-item>
      <el-form-item :label="i18nStore.t('farms.phone')"><el-input v-model="form.contact_phone" /></el-form-item>
      <el-form-item :label="i18nStore.t('farms.address')"><el-input v-model="form.address" /></el-form-item>
      <el-form-item :label="i18nStore.t('farms.status')">
        <el-select v-model="form.status">
          <el-option :label="i18nStore.t('common.active')" value="active" />
          <el-option :label="i18nStore.t('common.inactive')" value="inactive" />
        </el-select>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">{{ i18nStore.t("farms.cancel") }}</el-button>
      <el-button type="primary" :loading="saving" @click="submitForm">{{ i18nStore.t("farms.save") }}</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";

import { createRow, fetchRows, updateRow } from "../api/client";
import DataTableCard from "../components/common/DataTableCard.vue";
import { useI18nStore } from "../stores/i18n";

const rows = ref<Record<string, unknown>[]>([]);
const dialogVisible = ref(false);
const saving = ref(false);
const editingId = ref<number | null>(null);
const form = reactive({
  code: "",
  name: "",
  contact_name: "",
  contact_phone: "",
  address: "",
  status: "active"
});
const i18nStore = useI18nStore();
const columns = computed(() => [
  { prop: "code", label: i18nStore.t("farms.code") },
  { prop: "name", label: i18nStore.t("farms.name") },
  { prop: "contactName", label: i18nStore.t("farms.contact") },
  { prop: "contactPhone", label: i18nStore.t("farms.phone") },
  { prop: "status", label: i18nStore.t("farms.status") }
]);

async function loadRows() {
  rows.value = await fetchRows("/farms");
}

function resetForm() {
  editingId.value = null;
  form.code = "";
  form.name = "";
  form.contact_name = "";
  form.contact_phone = "";
  form.address = "";
  form.status = "active";
}

function openCreateDialog() {
  resetForm();
  dialogVisible.value = true;
}

function openEditDialog(row: Record<string, unknown>) {
  editingId.value = Number(row.id);
  form.code = String(row.code ?? "");
  form.name = String(row.name ?? "");
  form.contact_name = String(row.contactName ?? "");
  form.contact_phone = String(row.contactPhone ?? "");
  form.address = String(row.address ?? "");
  form.status = String(row.status ?? "active");
  dialogVisible.value = true;
}

async function submitForm() {
  saving.value = true;
  try {
    if (editingId.value) {
      await updateRow(`/farms/${editingId.value}`, form);
    } else {
      await createRow("/farms", form);
    }
    ElMessage.success(i18nStore.t("farms.saved"));
    dialogVisible.value = false;
    await loadRows();
  } finally {
    saving.value = false;
  }
}

onMounted(loadRows);
</script>
