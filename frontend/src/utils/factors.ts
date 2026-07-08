export const factorOptions = [
  { code: "w01010", name: "水温" },
  { code: "w01014", name: "pH" },
  { code: "w01001", name: "溶解氧" },
  { code: "w01017", name: "电导率" },
  { code: "w01003", name: "浊度" },
  { code: "w01019", name: "盐度" },
  { code: "w01018", name: "高锰酸盐指数" },
  { code: "w21003", name: "氨氮" },
  { code: "w21011", name: "总磷" },
  { code: "w21001", name: "总氮" },
  { code: "temperature", name: "温度" },
  { code: "humidity", name: "湿度" },
  { code: "ammonia", name: "氨气" },
  { code: "co2", name: "二氧化碳" },
  { code: "illumination", name: "光照" }
];

const factorNameMap = new Map(factorOptions.map((item) => [item.code, item.name]));
const englishNameMap = new Map([
  ["Temperature", "水温"],
  ["Dissolved Oxygen", "溶解氧"],
  ["Conductivity", "电导率"],
  ["Salinity", "盐度"],
  ["Ammonia", "氨氮"]
]);

export function readableFactorName(item: Record<string, unknown>) {
  const code = typeof item.sensorCode === "string" ? item.sensorCode : "";
  const mapped = factorNameMap.get(code);
  if (mapped) return mapped;

  const name = typeof item.sensorName === "string" ? item.sensorName : "";
  if (englishNameMap.has(name)) return englishNameMap.get(name);
  if (name && !/^w\d+/i.test(name)) return name;
  return "未命名因子";
}
