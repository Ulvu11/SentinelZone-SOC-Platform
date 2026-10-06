import { chromium } from "playwright";
import { expect } from "@playwright/test";
import fs from "node:fs/promises";
const base = "http://127.0.0.1:3000";
const browser = await chromium.launch({ channel: "chrome", headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const errors = [];
const results = {
  routes: [],
  links: [],
  viewports: [],
  interactions: [],
  errors,
};
page.on("pageerror", (error) => errors.push(error.message));
page.on("console", (message) => {
  if (message.type() === "error")
    errors.push(message.text() + " " + message.location().url);
});
const routes = [
  "/",
  "/overview",
  "/incidents",
  ...["INC-0042", "INC-0041", "INC-0040", "INC-0039", "INC-0038"].map(
    (id) => "/incidents/" + id,
  ),
  "/alerts",
  "/endpoints",
  ...["EP-001", "EP-002", "EP-003", "EP-004"].map((id) => "/endpoints/" + id),
  "/hardware",
  "/network",
  "/identity",
  "/honeypots",
  "/threat-hunting",
  "/mitre",
  "/ai-soc",
  "/purple-team",
  "/backup",
  "/reports",
  "/settings",
];
const links = new Set();
try {
  for (const route of routes) {
    const response = await page.goto(base + route);
    expect(response.status()).toBe(200);
    await expect(page.locator("main h1")).toBeVisible();
    await expect(page.locator("main")).not.toContainText(
      "This page could not be found",
    );
    const heading = await page.locator("main h1").innerText();
    const hrefs = await page
      .locator("a[href]")
      .evaluateAll((nodes) => nodes.map((node) => node.getAttribute("href")));
    hrefs
      .filter((href) => href.startsWith("/"))
      .forEach((href) => links.add(href));
    results.routes.push({ route, status: response.status(), heading });
    console.log("ROUTE PASS", route);
  }
  for (const href of links) {
    const response = await page.request.get(base + href);
    expect(response.status(), href).toBe(200);
    results.links.push(href);
  }
  const sidebar = await page
    .getByRole("navigation", { name: "Main navigation" })
    .getByRole("link")
    .evaluateAll((nodes) =>
      nodes.map((node) => ({
        label: node.getAttribute("aria-label"),
        href: node.getAttribute("href"),
      })),
    );
  for (const item of sidebar) {
    await page
      .getByRole("navigation", { name: "Main navigation" })
      .getByRole("link", { name: item.label, exact: true })
      .click();
    await expect(page).toHaveURL(base + item.href);
    await expect(page.locator("main h1")).toBeVisible();
    await expect(
      page
        .getByRole("navigation", { name: "Main navigation" })
        .getByRole("link", { name: item.label, exact: true }),
    ).toHaveAttribute("aria-current", "page");
  }
  results.interactions.push("All 15 sidebar links and active states");
  await page.goto(base + "/endpoints");
  await page.getByLabel("Search hostname, IP, user or OS").fill("FINANCE");
  await expect(page.locator("tbody tr")).toHaveCount(1);
  await page.getByRole("button", { name: "Clear search", exact: true }).click();
  await page.getByLabel("All endpoint statuses").selectOption("healthy");
  await expect(page.locator("tbody tr")).toHaveCount(2);
  await page.getByLabel("All endpoint statuses").selectOption("");
  await page.getByLabel("All security risks").selectOption("critical");
  await expect(page.locator("tbody tr")).toHaveCount(1);
  await page.getByLabel("All security risks").selectOption("");
  await page.getByLabel("All hardware risks").selectOption("high");
  await expect(page.locator("tbody tr")).toHaveCount(2);
  await page.getByLabel("All hardware risks").selectOption("");
  await page.getByLabel("Sort endpoints").selectOption("hostname");
  await expect(page.locator("tbody tr").first()).toContainText("DC01");
  await page.getByLabel("Sort endpoints").selectOption("security-desc");
  await page.locator("tbody tr").filter({ hasText: "FINANCE-PC-021" }).click();
  await expect(page).toHaveURL(base + "/endpoints/EP-001");
  await expect(
    page.getByRole("heading", { name: "FINANCE-PC-021", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Security Risk", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Hardware Risk", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("navigation", { name: "Endpoint sections" })
    .getByRole("link", { name: "Processes", exact: true })
    .click();
  await expect(page).toHaveURL(base + "/endpoints/EP-001#processes");
  await page
    .getByRole("navigation", { name: "Breadcrumb" })
    .getByRole("link", { name: "Endpoints", exact: true })
    .click();
  await expect(page).toHaveURL(base + "/endpoints");
  results.interactions.push(
    "Endpoint search, status/security/hardware filters, sorting, row navigation, sections and breadcrumb",
  );
  await page.goto(base + "/incidents");
  await page.getByLabel("All severities").selectOption("critical");
  await expect(page.locator("tbody tr")).toHaveCount(1);
  await page.getByLabel("All severities").selectOption("");
  await page.getByLabel("Time range").selectOption("1h");
  await expect(page.locator("tbody tr")).toHaveCount(2);
  await page.getByLabel("Time range").selectOption("24h");
  await expect(page.locator("tbody tr")).toHaveCount(5);
  await page.getByRole("link", { name: "INC-0042", exact: true }).click();
  await expect(
    page.getByRole("heading", {
      name: "Possible Resource Hijacking",
      exact: true,
    }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Analyze with AI", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "AI SOC Analysis", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("link", { name: "Back to Incidents", exact: true })
    .click();
  await expect(page).toHaveURL(base + "/incidents");
  results.interactions.push(
    "Incident filters, time range, detail, AI analysis and back link",
  );
  for (const [query, path] of [
    ["FINANCE-PC-021", "/endpoints/EP-001"],
    ["INC-0042", "/incidents/INC-0042"],
    ["185.220.101.42", "/incidents/INC-0042"],
    ["svhost64.exe", "/endpoints/EP-001#processes"],
    ["a.mammadov", "/endpoints/EP-001"],
    ["a84d716f23b987e15", "/incidents/INC-0042"],
  ]) {
    await page.keyboard.press("Control+k");
    await expect(page.getByRole("dialog")).toBeVisible();
    await page.getByLabel("Search SOC entities").fill(query);
    const result = page
      .getByRole("dialog")
      .locator("a")
      .filter({ hasText: query })
      .first();
    await expect(result).toBeVisible();
    expect(await result.getAttribute("href")).toBe(path);
    await result.click();
    await expect(page).toHaveURL(base + path);
    await expect(page.locator("main h1")).toBeVisible();
  }
  await page.keyboard.press("Control+k");
  await page.getByLabel("Search SOC entities").fill("no-such-entity-xyz");
  await expect(page.getByRole("dialog")).toContainText("No matching records");
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).not.toBeVisible();
  results.interactions.push(
    "Ctrl+K, six entity types, all result destinations, empty search and Escape",
  );
  await page.goto(base + "/threat-hunting");
  await page.getByLabel("Hunt query").fill("svhost64.exe");
  await page.getByRole("button", { name: "Run hunt", exact: true }).click();
  await expect(page.locator("tbody")).toContainText("svhost64.exe");
  await page.getByLabel("Entity type").selectOption("hash");
  await page.getByLabel("Hunt query").fill("a84d716");
  await page.getByRole("button", { name: "Run hunt", exact: true }).click();
  await expect(page.locator("tbody tr")).toHaveCount(1);
  await expect(page.locator("tbody")).toContainText("INC-0042");
  results.interactions.push("Threat hunt process and hash queries");
  await page.goto(base + "/ai-soc");
  await page
    .getByLabel("Investigation", { exact: true })
    .selectOption("INC-0041");
  await page
    .getByRole("button", { name: "Analyze evidence", exact: true })
    .click();
  await expect(page.locator("main")).toContainText(
    "Repeated SSH authentication attempts",
  );
  results.interactions.push(
    "AI workspace changes evidence with selected incident",
  );
  await page.goto(base + "/reports");
  await page
    .getByRole("button", { name: "Network Security Report", exact: false })
    .click();
  await expect(
    page.getByRole("heading", { name: "Network detections", exact: true }),
  ).toBeVisible();
  const downloaded = page.waitForEvent("download");
  await page
    .getByRole("button", { name: "Export report", exact: true })
    .click();
  const download = await downloaded;
  await download.saveAs("qa/exported-report.md");
  const report = await fs.readFile("qa/exported-report.md", "utf8");
  expect(report).toContain("NET-002");
  expect(report).toContain("\n\n");
  results.interactions.push("Report selection, preview and Markdown download");
  await page.goto(base + "/settings");
  await page.getByLabel("Table density").selectOption("compact");
  await expect(page.locator(".app-shell")).toHaveAttribute(
    "data-density",
    "compact",
  );
  await page.reload();
  await expect(page.getByLabel("Table density")).toHaveValue("compact");
  await page.getByLabel("Table density").selectOption("comfortable");
  await page
    .getByRole("button", { name: "Collapse sidebar", exact: true })
    .click();
  await expect(page.locator(".app-content")).toHaveCSS("margin-left", "68px");
  await page
    .getByRole("button", { name: "Expand sidebar", exact: true })
    .click();
  await expect(page.locator(".app-content")).toHaveCSS("margin-left", "240px");
  results.interactions.push(
    "Persisted appearance preferences and coordinated sidebar collapse",
  );
  for (const [width, height] of [
    [1920, 1080],
    [1600, 900],
    [1440, 900],
    [1366, 768],
    [1280, 800],
    [768, 1024],
  ]) {
    await page.setViewportSize({ width, height });
    for (const route of [
      "/",
      "/endpoints",
      "/endpoints/EP-001",
      "/incidents/INC-0042",
      "/network",
      "/ai-soc",
      "/settings",
    ]) {
      await page.goto(base + route);
      await expect(page.locator("main h1")).toBeVisible();
      const measurements = await page.evaluate(() => ({
        viewport: innerWidth,
        document: document.documentElement.scrollWidth,
        mainLeft: document.querySelector("main").getBoundingClientRect().left,
        sidebarRight: document.querySelector("aside").getBoundingClientRect()
          .right,
      }));
      expect(measurements.document, route + " at " + width).toBeLessThanOrEqual(
        width,
      );
      expect(measurements.mainLeft).toBeGreaterThanOrEqual(
        measurements.sidebarRight,
      );
      results.viewports.push({ width, height, route, ...measurements });
    }
    console.log("VIEWPORT PASS", width, height);
  }
  for (const [route, name] of [
    ["/", "overview"],
    ["/endpoints", "endpoints"],
    ["/endpoints/EP-001", "endpoint-detail"],
    ["/incidents/INC-0042", "incident-detail"],
    ["/ai-soc", "ai-soc"],
  ]) {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(base + route);
    await expect(page.locator("main h1")).toBeVisible();
    await page.screenshot({
      path: "qa/" + name + ".png",
      fullPage: true,
      caret: "initial",
    });
  }
  await page.setViewportSize({ width: 768, height: 1024 });
  await page.goto(base + "/endpoints");
  await page.screenshot({
    path: "qa/tablet-endpoints.png",
    fullPage: true,
    caret: "initial",
  });
  expect(errors).toEqual([]);
  console.log(
    "PASS",
    results.routes.length,
    "routes;",
    results.links.length,
    "internal links;",
    results.viewports.length,
    "responsive checks;",
    results.interactions.length,
    "interaction groups",
  );
} catch (error) {
  results.failure = String(error);
  await page.screenshot({
    path: "qa/failure.png",
    fullPage: true,
    caret: "initial",
  });
  console.error(error);
  process.exitCode = 1;
} finally {
  await fs.writeFile(
    "qa/browser-results.json",
    JSON.stringify(results, null, 2),
  );
  await browser.close();
}
