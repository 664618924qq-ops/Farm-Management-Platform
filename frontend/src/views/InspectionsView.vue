<template>
  <DataTableCard title="巡检记录" description="展示巡检项、结果、异常摘要、处理人、时间和状态，用于运行维护与验收复核。" :rows="rows" :columns="columns">
    <template #actions>
      <el-button type="primary" @click="dialogVisible = true">新增巡检</el-button>
    </template>
  </DataTableCard>

  <el-dialog v-model="dialogVisible" title="新增巡检记录" width="520px">
    <el-form :model="form" label-width="120px">
      <el-form-item label="养殖场 ID"><el-input-number v-model="form.farm_id" :min="1" /></el-form-item>
      <el-form-item label="棚舍 ID"><el-input-number v-model="form.shed_id" :min="1" /></el-form-item>
      <el-form-item label="处理人"><el-input v-model="form.inspector_name" /></el-form-item>
      <el-form-item label="巡检记录"><el-input v-model="form.notes" type="textarea" :rows="4" /></el-form-item>
      <el-form-item label="状态">
        <el-select v-model="form.status">
          <el-option label="已完成" value="completed" />
          <el-option label="需跟进" value="follow_up" />
        </el-select>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="submitForm">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";

import { createRow, fetchRows } from "../api/client";
import DataTableCard from "../components/common/DataTableCard.vue";

const rows = ref<Record<string, unknown>[]>([]);
const dialogVisible = ref(false);
const saving = ref(false);
const form = reactive({
  farm_id: 1,
  shed_id: 1,
  inspector_name: "",
  notes: "",
  status: "completed"
});
const columns = [
  { prop: "inspectionItem", label: "巡检项", minWidth: 180 },
  { prop: "result", label: "结果", minWidth: 100 },
  { prop: "abnormal", label: "异常/摘要", minWidth: 260 },
  { prop: "handler", label: "处理人", minWidth: 120 },
  { prop: "createdAtBeijing", label: "时间（北京）", minWidth: 210 },
  { prop: "statusLabel", label: "状态", minWidth: 100 }
];

async function loadRows() {
  rows.value = await fetchRows("/inspections");
}

async function submitForm() {
  saving.value = true;
  try {
    await createRow("/inspections", form);
    ElMessage.success("巡检记录已创建");
    dialogVisible.value = false;
    form.inspector_name = "";
    form.notes = "";
    form.status = "completed";
    await loadRows();
  } finally {
    saving.value = false;
  }
}

onMounted(loadRows);
</script>
