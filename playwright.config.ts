import { defineConfig, devices } from '@playwright/test';
import { BANCO_E2E, PORTA_APP, senhaSa } from './e2e/helpers/env';

/**
 * Testes E2E do app Streamlit contra um banco SÓ DE TESTE (CentralDeAr_E2E),
 * recriado do zero a cada execução pelo global-setup. O banco CentralDeAr e o .env
 * não são alterados: o app de teste recebe as variáveis de ambiente abaixo.
 *
 * Assistir: SLOW_MO=500 npx playwright test e2e/clientes.spec.ts --headed --workers=1 -g "CPF"
 */
export default defineConfig({
  testDir: './e2e',
  globalSetup: './e2e/global-setup.ts',
  timeout: 120_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 0,
  reporter: [['list'], ['html', { open: 'never' }]],

  use: {
    baseURL: `http://localhost:${PORTA_APP}`,
    viewport: { width: 1366, height: 768 },
    launchOptions: { slowMo: Number(process.env.SLOW_MO ?? 0) },
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    actionTimeout: 15_000,
  },

  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'], viewport: { width: 1366, height: 768 } } }],

  webServer: {
    command: `./.venv/bin/streamlit run app.py --server.port ${PORTA_APP} --server.headless true`,
    url: `http://localhost:${PORTA_APP}/_stcore/health`,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    env: {
      DB_MODE: 'docker',
      DB_NAME: BANCO_E2E,
      DB_PASSWORD: senhaSa(),
    },
  },
});
