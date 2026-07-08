import { computed, ref } from "vue";
import { defineStore } from "pinia";

export type Locale = "zh-CN" | "en-US";

type MessageLeaf = string;
type MessageTree = { [key: string]: MessageLeaf | MessageTree };

const STORAGE_KEY = "livestock-monitor-locale";

const messages: Record<Locale, MessageTree> = {
  "zh-CN": {
    layout: {
      title: "养殖场监测平台",
      subtitle: "跨养殖场查看环境、告警和巡检协同。",
      section: "运营总览",
      adminView: "管理员视角",
      workerView: "员工视角",
      fallbackPage: "控制台",
      switchLabel: "语言"
    },
    nav: {
      dashboard: "总览首页",
      farms: "养殖场管理",
      devices: "设备管理",
      sensors: "传感器管理",
      telemetry: "实时监测",
      protocol: "协议接收日志",
      alerts: "告警中心",
      inspections: "巡检记录"
    },
    login: {
      title: "养殖场监测平台",
      subtitle: "使用下面的演示账号登录。现在登录页已经接入真实后端接口。",
      demoAccounts: "演示管理员：admin / admin123 | 演示员工：worker / worker123",
      username: "用户名",
      password: "密码",
      signIn: "登录",
      success: "登录成功",
      failed: "登录失败，请检查账号或稍后重试。"
    },
    dashboard: {
      title: "养殖场监测总览",
      subtitle: "集中查看多养殖场环境数据、告警状态和设备健康情况。",
      autoRefresh: "总览自动刷新中",
      farms: "养殖场数量",
      farmsHint: "已纳入平台管理",
      sheds: "棚舍数量",
      shedsHint: "已覆盖监测区域",
      devices: "在线设备",
      devicesHint: "当前活跃网关",
      alerts: "活动告警",
      alertsHint: "需要尽快处理"
    },
    farms: {
      title: "养殖场管理",
      description: "维护养殖场基础信息，供总览和设备归属使用。",
      add: "新增养殖场",
      edit: "编辑",
      actions: "操作",
      createTitle: "新增养殖场",
      editTitle: "编辑养殖场",
      code: "编码",
      name: "名称",
      contact: "联系人",
      phone: "联系电话",
      address: "地址",
      status: "状态",
      cancel: "取消",
      save: "保存",
      saved: "养殖场已保存"
    },
    devices: {
      title: "设备管理",
      description: "查看网关、协议类型和在线状态，为后续 PC 工具接入做准备。",
      code: "设备编码",
      name: "名称",
      type: "设备类型",
      protocol: "协议",
      status: "状态"
    },
    sensors: {
      title: "传感器管理",
      description: "维护指标定义、单位和阈值，告警规则也基于这里。",
      code: "指标编码",
      name: "指标名称",
      unit: "单位",
      low: "下限",
      high: "上限"
    },
    telemetry: {
      title: "实时监测",
      description: "读取平台最新遥测数据，快速查看当前指标情况。",
      refresh: "立即刷新",
      autoRefresh: "自动刷新中",
      empty: "暂时还没有接收到监测数据，请先让 PC 端上传报文。",
      deviceId: "设备ID",
      metric: "指标",
      value: "当前值",
      unit: "单位",
      quality: "状态标记",
      recordedAt: "采集时间"
    },
    protocol: {
      title: "协议接收日志",
      description: "查看 PC 工具通过 HTTP 或 TCP 上传的原始报文、解析状态和平台应答。",
      refresh: "立即刷新",
      autoRefresh: "自动刷新中",
      source: "来源",
      mn: "设备 MN",
      cn: "命令 CN",
      qn: "请求 QN",
      dataTime: "数据时间",
      status: "状态",
      metricCount: "指标数",
      receivedAt: "接收时间",
      rawPacket: "原始报文",
      ackPacket: "平台应答",
      errorMessage: "错误原因",
      emptyAck: "暂无应答",
      emptyError: "无"
    },
    alerts: {
      title: "告警中心",
      description: "员工可在这里确认告警，管理员可统一查看活动异常。",
      actions: "操作",
      acknowledge: "确认",
      metricCode: "指标编码",
      level: "告警级别",
      message: "告警内容",
      status: "状态"
    },
    inspections: {
      title: "巡检记录",
      description: "记录现场巡检结果，后续可以继续补照片或附件。",
      add: "新增巡检",
      createTitle: "新增巡检记录",
      farmId: "养殖场ID",
      shedId: "棚舍ID",
      inspector: "巡检人",
      notes: "巡检内容",
      status: "状态",
      createdAt: "创建时间",
      cancel: "取消",
      save: "保存",
      created: "巡检记录已创建"
    },
    common: {
      refresh: "刷新",
      completed: "已完成",
      followUp: "待跟进",
      active: "启用",
      inactive: "停用"
    }
  },
  "en-US": {
    layout: {
      title: "Farm Monitoring Platform",
      subtitle: "Monitor environment, alerts, and inspections across multiple farms.",
      section: "Operations",
      adminView: "Admin View",
      workerView: "Worker View",
      fallbackPage: "Control Center",
      switchLabel: "Language"
    },
    nav: {
      dashboard: "Dashboard",
      farms: "Farms",
      devices: "Devices",
      sensors: "Sensors",
      telemetry: "Telemetry",
      protocol: "Protocol Logs",
      alerts: "Alerts",
      inspections: "Inspections"
    },
    login: {
      title: "Farm Monitoring Platform",
      subtitle: "Sign in with the demo accounts below. The login screen now talks to the real backend response.",
      demoAccounts: "Demo admin: admin / admin123 | Demo worker: worker / worker123",
      username: "Username",
      password: "Password",
      signIn: "Sign in",
      success: "Login successful",
      failed: "Login failed. Please check your account or try again later."
    },
    dashboard: {
      title: "Farm Monitoring Overview",
      subtitle: "Track multi-farm environmental telemetry, alerts, and device health from one web platform.",
      autoRefresh: "Dashboard auto refreshing",
      farms: "Farms",
      farmsHint: "Included in platform management",
      sheds: "Sheds",
      shedsHint: "Covered monitoring areas",
      devices: "Online Devices",
      devicesHint: "Current active gateways",
      alerts: "Active Alerts",
      alertsHint: "Need attention soon"
    },
    farms: {
      title: "Farm Management",
      description: "Maintain base farm information for dashboards and device ownership.",
      add: "Add Farm",
      edit: "Edit",
      actions: "Actions",
      createTitle: "Create Farm",
      editTitle: "Edit Farm",
      code: "Code",
      name: "Name",
      contact: "Contact",
      phone: "Phone",
      address: "Address",
      status: "Status",
      cancel: "Cancel",
      save: "Save",
      saved: "Farm saved"
    },
    devices: {
      title: "Device Management",
      description: "Review gateways, protocol types, and online status before PC tool integration.",
      code: "Device Code",
      name: "Name",
      type: "Device Type",
      protocol: "Protocol",
      status: "Status"
    },
    sensors: {
      title: "Sensor Management",
      description: "Maintain metric definitions, units, and thresholds used by alert rules.",
      code: "Metric Code",
      name: "Metric Name",
      unit: "Unit",
      low: "Low Limit",
      high: "High Limit"
    },
    telemetry: {
      title: "Live Telemetry",
      description: "Read the latest platform telemetry for a quick on-site view of current metrics.",
      refresh: "Refresh now",
      autoRefresh: "Auto refreshing",
      empty: "No telemetry has been received yet. Send a packet from the PC tool first.",
      deviceId: "Device ID",
      metric: "Metric",
      value: "Value",
      unit: "Unit",
      quality: "Quality",
      recordedAt: "Collected At"
    },
    protocol: {
      title: "Protocol Receive Logs",
      description: "Review raw packets uploaded by the PC tool over HTTP or TCP, including parse status and platform replies.",
      refresh: "Refresh now",
      autoRefresh: "Auto refreshing",
      source: "Source",
      mn: "Device MN",
      cn: "Command CN",
      qn: "Request QN",
      dataTime: "Data Time",
      status: "Status",
      metricCount: "Metrics",
      receivedAt: "Received At",
      rawPacket: "Raw Packet",
      ackPacket: "Platform ACK",
      errorMessage: "Error",
      emptyAck: "No ACK",
      emptyError: "None"
    },
    alerts: {
      title: "Alert Center",
      description: "Workers can acknowledge alerts here, while managers review active issues.",
      actions: "Actions",
      acknowledge: "Acknowledge",
      metricCode: "Metric Code",
      level: "Level",
      message: "Message",
      status: "Status"
    },
    inspections: {
      title: "Inspection Records",
      description: "Capture worker inspections now, with room to add attachments later.",
      add: "Add Inspection",
      createTitle: "Create Inspection",
      farmId: "Farm ID",
      shedId: "Shed ID",
      inspector: "Inspector",
      notes: "Notes",
      status: "Status",
      createdAt: "Created At",
      cancel: "Cancel",
      save: "Save",
      created: "Inspection created"
    },
    common: {
      refresh: "Refresh",
      completed: "completed",
      followUp: "follow_up",
      active: "active",
      inactive: "inactive"
    }
  }
};

function getMessage(locale: Locale, path: string): string {
  const result = path.split(".").reduce<MessageLeaf | MessageTree | undefined>((acc, segment) => {
    if (typeof acc === "string" || acc === undefined) {
      return undefined;
    }
    return acc[segment];
  }, messages[locale]);

  return typeof result === "string" ? result : path;
}

export const useI18nStore = defineStore("i18n", () => {
  const locale = ref<Locale>((localStorage.getItem(STORAGE_KEY) as Locale | null) ?? "zh-CN");
  const isChinese = computed(() => locale.value === "zh-CN");

  function setLocale(next: Locale) {
    locale.value = next;
    localStorage.setItem(STORAGE_KEY, next);
  }

  function toggleLocale() {
    setLocale(locale.value === "zh-CN" ? "en-US" : "zh-CN");
  }

  function t(path: string) {
    return getMessage(locale.value, path);
  }

  return {
    locale,
    isChinese,
    setLocale,
    toggleLocale,
    t
  };
});
