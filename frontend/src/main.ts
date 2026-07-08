import { createApp } from "vue";
import { createPinia } from "pinia";
import ElementPlus from "element-plus";
import "element-plus/dist/index.css";

import App from "./App.vue";
import router from "./router";
import { useAuthStore } from "./stores/auth";
import "./styles.css";

const app = createApp(App);
const pinia = createPinia();

app.use(pinia).use(router).use(ElementPlus);
useAuthStore(pinia).hydrate();
app.mount("#app");
