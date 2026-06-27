import { defineConfig, devices } from "@playwright/test";

// The full stack is already running:
//   frontend http://localhost:8080
//   backend  http://localhost:8000
// So we deliberately do NOT configure a `webServer` block here.
export default defineConfig({
  testDir: "./specs",
  timeout: 90_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  retries: 0,
  reporter: "line",
  use: {
    baseURL: "http://localhost:8080",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    actionTimeout: 15_000,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
