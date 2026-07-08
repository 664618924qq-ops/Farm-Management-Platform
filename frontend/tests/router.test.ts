import { describe, expect, it } from "vitest";

import { routes } from "../src/router";

describe("router", () => {
  it("includes dashboard route", () => {
    expect(routes.some((route) => route.path === "/")).toBe(true);
  });

  it("includes protocol logs route", () => {
    const layoutRoute = routes.find((route) => route.path === "/");
    expect(layoutRoute?.children?.some((route) => route.path === "protocol")).toBe(true);
  });

  it("includes data query and analysis routes", () => {
    const layoutRoute = routes.find((route) => route.path === "/");
    expect(layoutRoute?.children?.some((route) => route.path === "data-query")).toBe(true);
    expect(layoutRoute?.children?.some((route) => route.path === "analysis")).toBe(true);
  });
});
