import { expect, test, type Page } from "@playwright/test";

const requests = Array.from({ length: 100_000 }, (_, index) => ({
  id: `request-${index}`,
  team: "test-team",
  user: `user-${String(index).padStart(5, "0")}`,
  ts: "2026-09-21T12:00:00Z",
  model: "test-model",
  provider: "test-provider",
  action: index % 3 === 0 ? "blocked" : "allowed",
  policy_version: 1,
  shadow: false,
  blocked_reason: index % 3 === 0 ? "Sensitive data matched policy." : null,
  prompt_tokens: 12,
  completion_tokens: 8,
  cost_cents: 3,
  latency_ms: 20,
  provider_latency_ms: 15,
  status_code: 200,
  fallback_used: false,
}));

const stats = {
  range: "7d",
  sampled: 200,
  by_action: { allowed: 80, masked: 40, blocked: 60, shadow: 20 },
  totals: { today: 20, last_7d: 200, last_30d: 600 },
  windowed_total: 200,
  sensitive_requests: 120,
  sensitive_pct: 0.6,
  sparkline: [{ day: "2026-09-21", count: 200 }],
  top_entity_types: [{ entity_type: "PERSON", count: 80 }],
  top_teams: [{ team: "test-team", count: 200, flagged: 120 }],
  top_users: [
    { user: "most-flagged@example.com", count: 25, flagged: 20 },
    { user: "other@example.com", count: 30, flagged: 4 },
  ],
  spend_by_provider: [{ provider: "test-provider", cost_cents: 30 }],
  spend_by_model: [{ model: "test-model", cost_cents: 30 }],
};

const ruleset = {
  version: 1,
  default_action: "allow",
  shadow_mode: false,
  rules: [],
};

async function stubAdminApi(page: Page) {
  const reported = new Set<string>();
  await page.route("**/admin/**", async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname;
    const method = route.request().method();
    const json = (body: unknown) =>
      route.fulfill({ contentType: "application/json", body: JSON.stringify(body) });

    if (path === "/admin/stats/overview") return json(stats);
    if (path === "/admin/stats/top-users") return json({ range: "7d", items: stats.top_users });
    if (path === "/admin/stats/detections") {
      return json({ range: "7d", by_entity_type: { PERSON: { total: 20, at_confidence: { "0.5": 20 } } } });
    }
    if (path === "/admin/stats/false-positives") return json({ range: "7d", total: 2, reported: reported.size, rate: reported.size / 2 });
    if (path === "/admin/teams") return json({ items: [{ id: "team-1", name: "test-team", shadow_mode: false, monthly_budget_cents: 0, rate_limit_rpm: 60, allowed_models: [], content_capture_enabled: false }] });
    if (path === "/admin/policies") {
      if (method === "POST") return json({ ...ruleset, version: 2 });
      return json(ruleset);
    }
    if (path === "/admin/policies/versions") return json({ active_version: 1, versions: [ruleset] });
    if (path === "/admin/policies/test") {
      return json({ policy_version: 1, masked_text: "Email me at <PERSON_1>", findings: [{ entity_type: "PERSON", confidence: 0.99, detector: "test", span: [12, 17], action: "pseudonymize", rule_id: "person-rule", reason: "Policy matched." }] });
    }
    if (path === "/admin/policies/2/activate") return json({ ...ruleset, version: 2 });
    if (path === "/admin/requests") {
      const action = url.searchParams.get("action");
      const source = action === "blocked" ? requests.filter((item) => item.action === "blocked") : requests;
      return json({ items: source.slice(0, 100), next_cursor: "page-2" });
    }
    if (path.endsWith("/trace")) {
      return json({ request_id: "request-0", trace: [
        { id: "finding-a", entity_type: "PERSON", detector: "test", confidence: 0.99, span: [0, 4], matched_rule_id: "person-rule", action: "block", was_shadow: false, reason: "First finding.", false_positive_reported: reported.has("finding-a") },
        { id: "finding-b", entity_type: "PERSON", detector: "test", confidence: 0.98, span: [5, 9], matched_rule_id: "person-rule", action: "block", was_shadow: false, reason: "Second finding.", false_positive_reported: reported.has("finding-b") },
      ] });
    }
    if (method === "POST" && path.startsWith("/admin/findings/")) {
      reported.add(path.split("/").at(-2) ?? "");
      return json({ finding_id: path.split("/").at(-2), false_positive_reported: true });
    }
    return json({ items: [] });
  });
}

test.beforeEach(async ({ page }) => stubAdminApi(page));

test("AC-M6-01: Overview identifies the most flagged sender", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
  await expect(page.getByText("Top users by flagged volume")).toBeVisible();
  await expect(page.getByText("most-flagged@example.com")).toBeVisible();
  await expect(page.getByText("20 flagged / 25")).toBeVisible();
});

test("AC-M6-02: policy editor previews a PERSON pseudonymization before save", async ({ page }) => {
  await page.goto("/policy");
  await page.getByLabel("PERSON pseudonymize").check();
  await page.getByRole("button", { name: "Test prompt" }).click();
  await expect(page.getByText("The model would receive:")).toBeVisible();
  await expect(page.getByText("Email me at <PERSON_1>")).toBeVisible();
  await page.getByTestId("review-save").click();
  await expect(page.getByRole("heading", { name: "Review policy change" })).toBeVisible();
  await expect(page.locator("pre").filter({ hasText: "action: pseudonymize" })).toBeVisible();
});

test("AC-M6-03: request explorer limits DOM work for a 100k-record corpus", async ({ page }) => {
  let requestUrl = "";
  page.on("request", (request) => {
    if (request.url().includes("/admin/requests")) requestUrl = request.url();
  });
  await page.goto("/requests");
  await expect(page.getByText("user-00000")).toBeVisible();
  await expect.poll(() => new URL(requestUrl).searchParams.get("limit")).toBe("100");
  expect(await page.locator("tbody tr").count()).toBeLessThanOrEqual(100);
});

test("AC-M6-04: policy editor supports keyboard-only navigation", async ({ page }) => {
  await page.goto("/policy");
  await page.keyboard.press("Tab");
  await expect(page.locator(":focus-visible")).toHaveCount(1);
  await page.getByLabel("PERSON pseudonymize").focus();
  await page.keyboard.press("Space");
  await expect(page.getByLabel("PERSON pseudonymize")).toBeChecked();
  await page.getByTestId("review-save").focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("heading", { name: "Review policy change" })).toBeVisible();
  await page.getByRole("button", { name: "Cancel" }).focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("heading", { name: "Review policy change" })).not.toBeVisible();
});

test("AC-M6-05: dashboard chromatic utility classes are outcome-only", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
  const colourClasses = await page.locator("[class]").evaluateAll((elements) =>
    elements.flatMap((element) =>
      [...element.classList].filter((name) => /^(?:bg|text|border)-(?:blocked|masked|shadow)/.test(name)),
    ),
  );
  expect(colourClasses).toEqual(expect.arrayContaining(["bg-blocked", "bg-masked", "bg-shadow"]));
  expect(colourClasses.every((name) => /^(?:bg|text|border)-(?:blocked|masked|shadow)/.test(name))).toBe(true);
});

test("per-finding false-positive reporting affects only the selected finding", async ({ page }) => {
  await page.goto("/blocked");
  await page.getByRole("button", { name: "View trace" }).first().click();
  const first = page.locator("li", { hasText: "First finding." });
  const second = page.locator("li", { hasText: "Second finding." });
  await first.getByRole("button", { name: "Mark false positive" }).click();
  await expect(first.getByText("false positive reported")).toBeVisible();
  await expect(first.getByRole("button", { name: "Mark false positive" })).toHaveCount(0);
  await expect(second.getByRole("button", { name: "Mark false positive" })).toBeVisible();
});
