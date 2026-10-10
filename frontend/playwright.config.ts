import { defineConfig, devices } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 60000,
  use: { baseURL: "http://127.0.0.1:15173", trace: "retain-on-failure" },
  webServer: [
    {
      command: "../.venv/bin/python ../scripts/e2e_backend.py",
      url: "http://127.0.0.1:18080/api/health/",
      reuseExistingServer: false,
      timeout: 120000,
    },
    {
      command: "npm run dev -- --port 15173 --strictPort",
      env: { VITE_PROXY_TARGET: "http://127.0.0.1:18080" },
      url: "http://127.0.0.1:15173",
      reuseExistingServer: false,
    },
  ],
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile", use: { ...devices["Pixel 7"] } },
  ],
});
