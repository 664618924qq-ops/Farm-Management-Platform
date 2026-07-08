import axios from "axios";

const apiClient = axios.create({
  baseURL: "http://127.0.0.1:8000/api/v1",
  timeout: 10000
});

export type AuthUser = {
  id: number;
  username: string;
  displayName: string;
  role: string;
};

export type LoginResponse = {
  token: string;
  user: AuthUser;
};

export type DashboardSummary = {
  farmCount: number;
  shedCount: number;
  onlineDeviceCount: number;
  activeAlertCount: number;
  integrationStatus: {
    lastPacketTime: string | null;
    lastDevice: string | null;
    lastStatus: string | null;
    lastReceiveResult: string | null;
    lastCommand: string | null;
    lastMetricCount: number;
    lastAckStatus: string | null;
    lastAckSummary: string | null;
  };
};

export type TrendSeries = {
  sensorCode: string;
  points: Array<{ time: string; value: number; unit: string }>;
};

export type TableRow = Record<string, unknown>;

export type ProtocolLog = {
  id: number;
  source: string;
  mn: string | null;
  cn: string | null;
  qn: string | null;
  dataTime: string | null;
  dataTimeBeijing: string | null;
  status: string;
  metricCount: number;
  rawPacket: string;
  ackPacket: string | null;
  errorMessage: string | null;
  receivedAt: string;
  receivedAtBeijing: string;
  storedAtBeijing: string;
};

export type ProtocolLogQuery = {
  cn?: string;
  mn?: string;
  status?: string;
  startTime?: string;
  endTime?: string;
};

export type DataQueryResponse = {
  cn: string;
  mode: string;
  timeSemantics: string;
  timezone: string;
  dataSource: string;
  items: TableRow[];
};

export type AnalysisResponse = {
  cn: string;
  timezone: string;
  dataSource: string;
  summary: {
    recordCount: number;
    sensorCount: number;
    findingCount: number;
  };
  series: Array<{
    sensorCode: string;
    sensorName: string;
    unit: string;
    min: number;
    max: number;
    avg: number;
    points: Array<{ time: string | null; value: number }>;
    threshold: Record<string, unknown> | null;
    basis: string;
  }>;
  findings: Array<Record<string, unknown>>;
  suggestions: string[];
};

export function setAuthToken(token: string | null) {
  if (token) {
    apiClient.defaults.headers.common.Authorization = `Bearer ${token}`;
  } else {
    delete apiClient.defaults.headers.common.Authorization;
  }
}

export async function loginRequest(username: string, password: string): Promise<LoginResponse> {
  const response = await apiClient.post<LoginResponse>("/auth/login", { username, password });
  return response.data;
}

export async function fetchDashboardSummary(): Promise<DashboardSummary> {
  const response = await apiClient.get<DashboardSummary>("/dashboard/summary");
  return response.data;
}

export async function fetchDashboardTrends(): Promise<TrendSeries[]> {
  const response = await apiClient.get<TrendSeries[]>("/dashboard/trends");
  return response.data;
}

export async function fetchRows(path: string): Promise<TableRow[]> {
  const response = await apiClient.get<TableRow[]>(path);
  return response.data;
}

export async function fetchProtocolLogs(params?: ProtocolLogQuery): Promise<ProtocolLog[]> {
  const response = await apiClient.get<ProtocolLog[]>("/protocol/logs", { params });
  return response.data;
}

export async function fetchDataQuery(params: Record<string, string | number | undefined>): Promise<DataQueryResponse> {
  const response = await apiClient.get<DataQueryResponse>("/data/query", { params });
  return response.data;
}

export async function fetchAnalysis(params: Record<string, string | number | undefined>): Promise<AnalysisResponse> {
  const response = await apiClient.get<AnalysisResponse>("/data/analysis", { params });
  return response.data;
}

export async function createRow(path: string, payload: Record<string, unknown>): Promise<TableRow> {
  const response = await apiClient.post<TableRow>(path, payload);
  return response.data;
}

export async function updateRow(path: string, payload: Record<string, unknown>): Promise<TableRow> {
  const response = await apiClient.put<TableRow>(path, payload);
  return response.data;
}

export async function acknowledgeAlert(alertId: number): Promise<void> {
  await apiClient.post(`/alerts/${alertId}/acknowledge`);
}
