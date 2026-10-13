import { fileURLToPath } from "node:url";
import { defineConfig, devices } from "@playwright/test";
import { ADDABLE_PROJECT } from "./e2e/fixturePaths";

const port = Number(process.env.DELPHI_CODE_E2E_PORT ?? 8765);
const python = process.env.DELPHI_CODE_PYTHON ?? fileURLToPath(new URL("../.venv/bin/python", import.meta.url));

export default defineConfig({
  testDir: "e2e",
  forbidOnly: Boolean(process.env.CI),
  workers: 1,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: `http://127.0.0.1:${port}`,
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: `"${python}" ../tests/e2e_server.py`,
    url: `http://127.0.0.1:${port}/`,
    env: {
      DELPHI_CODE_E2E_PORT: String(port),
      DELPHI_CODE_E2E_TOKEN: "e2e-token",
      DELPHI_CODE_E2E_ADDABLE_PROJECT: ADDABLE_PROJECT,
    },
    reuseExistingServer: false,
    timeout: 60_000,
  },
});
