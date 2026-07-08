<template>
  <div class="login-page">
    <section class="login-card">
      <div>
        <h1>{{ i18nStore.t("login.title") }}</h1>
        <p>{{ i18nStore.t("login.subtitle") }}</p>
      </div>
      <el-alert :title="i18nStore.t('login.demoAccounts')" type="success" :closable="false" />
      <el-form class="login-form" :model="form" label-position="top" @submit.prevent="handleLogin">
        <el-form-item :label="i18nStore.t('login.username')">
          <el-input v-model="form.username" />
        </el-form-item>
        <el-form-item :label="i18nStore.t('login.password')">
          <el-input v-model="form.password" type="password" show-password />
        </el-form-item>
        <el-button class="login-button" type="primary" :loading="loading" @click="handleLogin">
          {{ i18nStore.t("login.signIn") }}
        </el-button>
      </el-form>
    </section>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";

import { useAuthStore } from "../stores/auth";
import { useI18nStore } from "../stores/i18n";

const router = useRouter();
const authStore = useAuthStore();
const i18nStore = useI18nStore();
const loading = ref(false);
const form = reactive({
  username: "admin",
  password: "admin123"
});

async function handleLogin() {
  loading.value = true;
  try {
    await authStore.login(form.username, form.password);
    ElMessage.success(i18nStore.t("login.success"));
    await router.push("/dashboard");
  } catch {
    ElMessage.error(i18nStore.t("login.failed"));
  } finally {
    loading.value = false;
  }
}
</script>
