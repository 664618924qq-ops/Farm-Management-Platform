import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";

import { useI18nStore } from "../src/stores/i18n";

describe("i18n store", () => {
  beforeEach(() => {
    localStorage.clear();
    setActivePinia(createPinia());
  });

  it("defaults to Chinese and can switch to English", () => {
    const store = useI18nStore();

    expect(store.locale).toBe("zh-CN");
    expect(store.t("dashboard.title")).toBe("养殖场监测总览");
    expect(store.t("nav.protocol")).toBe("协议接收日志");

    store.setLocale("en-US");

    expect(store.locale).toBe("en-US");
    expect(store.t("dashboard.title")).toBe("Farm Monitoring Overview");
    expect(store.t("nav.protocol")).toBe("Protocol Logs");
  });
});
