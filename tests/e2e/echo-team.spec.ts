// EchoTeam E2E Tests with Playwright
import { test, expect, describe } from "@playwright/test";

describe("EchoTeam Dashboard", () => {
  test("should load the dashboard", async ({ page }) => {
    await page.goto("http://localhost:5173");

    // Wait for the page to load
    await page.waitForLoadState("networkidle");

    // Check for the main heading
    await expect(page.locator("h1")).toContainText("EchoTeam");
  });

  test("should display clone cards", async ({ page }) => {
    await page.goto("http://localhost:5173");
    await page.waitForLoadState("networkidle");

    // Check for clone cards
    const cloneCards = page.locator(".clone-card");
    await expect(cloneCards).toHaveCount(3);

    // Verify each clone type
    await expect(page.locator(".clone-icon.calendar")).toBeVisible();
    await expect(page.locator(".clone-icon.email")).toBeVisible();
    await expect(page.locator(".clone-icon.ops")).toBeVisible();
  });

  test("should display action queue", async ({ page }) => {
    await page.goto("http://localhost:5173");
    await page.waitForLoadState("networkidle");

    // Check for action queue section
    await expect(page.locator(".action-queue h2")).toContainText("Action Queue");
  });

  test("should display stats cards", async ({ page }) => {
    await page.goto("http://localhost:5173");
    await page.waitForLoadState("networkidle");

    // Check for stats grid
    const statsGrid = page.locator(".stats-grid");
    await expect(statsGrid).toBeVisible();
  });

  test("should have responsive design", async ({ page }) => {
    await page.goto("http://localhost:5173");
    await page.setViewportSize({ width: 375, height: 667 });
    await page.waitForLoadState("networkidle");

    // Should still show content on mobile
    await expect(page.locator("h1")).toBeVisible();
  });
});

describe("API Endpoints", () => {
  test("health endpoint should respond", async ({ request }) => {
    const response = await request.get("http://localhost:3001/health");
    expect(response.status()).toBe(200);
    const data = await response.json();
    expect(data.status).toBe("ok");
  });

  test("clones endpoint should return data", async ({ request }) => {
    const response = await request.get("http://localhost:3001/api/clones");
    expect(response.status()).toBe(200);
    const data = await response.json();
    expect(data.clones).toBeDefined();
    expect(Array.isArray(data.clones)).toBe(true);
  });

  test("pending actions endpoint should respond", async ({ request }) => {
    const response = await request.get("http://localhost:3001/api/actions/pending");
    expect(response.status()).toBe(200);
    const data = await response.json();
    expect(data.actions).toBeDefined();
  });
});

describe("AI Service", () => {
  test("AI service health should respond", async ({ request }) => {
    const response = await request.get("http://localhost:8000/health");
    expect(response.status()).toBe(200);
    const data = await response.json();
    expect(data.status).toBe("ok");
  });

  test("Ollama models endpoint should list models", async ({ request }) => {
    const response = await request.get("http://localhost:8000/api/ollama/models");
    expect(response.status()).toBe(200);
    const data = await response.json();
    expect(data.models).toBeDefined();
    expect(data.configured_models).toBeDefined();
  });

  test("Ollama generate should work", async ({ request }) => {
    const response = await request.post("http://localhost:8000/api/ollama/generate", {
      data: {
        prompt: "What is EchoTeam?",
        model: "qwen2.5-coder:3b",
      },
    });
    expect(response.status()).toBe(200);
    const data = await response.json();
    expect(data.response).toBeDefined();
    expect(data.model).toBe("qwen2.5-coder:3b");
  });
});
