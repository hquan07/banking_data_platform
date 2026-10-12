import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, test } from '@playwright/test';

function rootEnvironment() {
  const repositoryRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');
  const environmentPath = path.join(repositoryRoot, '.env');
  if (!fs.existsSync(environmentPath)) return {};
  const entries = fs.readFileSync(environmentPath, 'utf8')
    .split(/\r?\n/)
    .filter(line => line && !line.startsWith('#') && line.includes('='))
    .map(line => {
      const separator = line.indexOf('=');
      return [line.slice(0, separator), line.slice(separator + 1)];
    });
  return Object.fromEntries(entries);
}

const environment = rootEnvironment();

function browserToken() {
  const payload = Buffer.from(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + 3600 })).toString('base64url');
  return `header.${payload}.signature`;
}

const runFixtures = [
  {
    run_id: '11111111-1111-4111-8111-111111111111', status: 'RUNNING', version: 2,
    owner_user_id: 1, owner_username: 'admin', source_kind: 'BENCHMARK_REPLAY',
    dataset_id: 'ds3_paysim', dataset_version: 'paysim-v2', requested_rate: 50,
    updated_at: '2026-10-12T01:00:00Z', progress: { processed: 750, total: 1000, percent: 75, lag: 250, partitions: 2 },
    quality: { status: 'running', reason: null, data_age_seconds: 600, sla_threshold_seconds: 300, reconciliation_checks: 4, reconciliation_completeness: 1 },
  },
  {
    run_id: '22222222-2222-4222-8222-222222222222', status: 'COMPLETED', version: 3,
    owner_user_id: 1, owner_username: 'admin', source_kind: 'BENCHMARK_REPLAY',
    dataset_id: 'ds1_creditcard', dataset_version: 'card-v1', requested_rate: 100,
    updated_at: '2026-10-12T01:02:00Z', progress: { processed: 1000, total: 1000, percent: 100, lag: 0, partitions: 1 },
    quality: { status: 'completed', reason: null, data_age_seconds: 20, sla_threshold_seconds: 300, reconciliation_checks: 5, reconciliation_completeness: 1 },
  },
  {
    run_id: '33333333-3333-4333-8333-333333333333', status: 'FAILED', version: 4,
    owner_user_id: 1, owner_username: 'admin', source_kind: 'MANUAL_REPLAY',
    dataset_id: 'ds4_baf', dataset_version: 'baf-v1', requested_rate: 10,
    updated_at: '2026-10-12T01:04:00Z', failure_reason: 'source contract rejected',
    progress: { processed: 5, total: 100, percent: 5, lag: 95, partitions: 1 },
    quality: { status: 'failed', reason: 'source contract rejected', data_age_seconds: 30, sla_threshold_seconds: 300, reconciliation_checks: 1, reconciliation_completeness: 0 },
  },
  {
    run_id: '44444444-4444-4444-8444-444444444444', status: 'PAUSED', version: 5,
    owner_user_id: 1, owner_username: 'admin', source_kind: 'BENCHMARK_REPLAY',
    dataset_id: 'ds3_paysim', dataset_version: 'paysim-v2', requested_rate: 25,
    updated_at: '2026-10-12T01:05:00Z', progress: { processed: 400, total: 1000, percent: 40, lag: 600, partitions: 2 },
    quality: { status: 'idle', reason: null, data_age_seconds: 30, sla_threshold_seconds: 300, reconciliation_checks: 4, reconciliation_completeness: .5 },
  },
  {
    run_id: '55555555-5555-4555-8555-555555555555', status: 'RUNNING', version: 1,
    owner_user_id: 1, owner_username: 'admin', source_kind: 'BENCHMARK_REPLAY',
    dataset_id: 'ds1_creditcard', dataset_version: 'card-v1', requested_rate: 20,
    updated_at: '2026-10-12T01:06:00Z', progress: { processed: 20, total: 100, percent: 20, lag: 80, partitions: 1 },
    quality: { status: 'running', reason: null, data_age_seconds: 10, sla_threshold_seconds: 300, reconciliation_checks: 1, reconciliation_completeness: 1 },
  },
  {
    run_id: '66666666-6666-4666-8666-666666666666', status: 'PAUSED', version: 1,
    owner_user_id: 1, owner_username: 'admin', source_kind: 'BENCHMARK_REPLAY',
    dataset_id: 'ds3_paysim', dataset_version: 'paysim-v2', requested_rate: 0,
    updated_at: '2026-10-12T01:07:00Z', progress: { processed: 10, total: 100, percent: 10, lag: 90, partitions: 1 },
    quality: { status: 'idle', reason: 'operator_paused', data_age_seconds: 20, sla_threshold_seconds: 300, reconciliation_checks: 1, reconciliation_completeness: 1 },
  },
  {
    run_id: '77777777-7777-4777-8777-777777777777', status: 'CREATED', version: 1,
    owner_user_id: 1, owner_username: 'admin', source_kind: 'MANUAL_REPLAY',
    dataset_id: 'ds4_baf', dataset_version: 'baf-v1', requested_rate: 0,
    updated_at: '2026-10-12T01:08:00Z', progress: null, quality: {},
  },
];

function capabilityFixture() {
  const support = {
    live: ['overview', 'fraud', 'datasets'],
    ds1_creditcard: ['overview', 'fraud', 'datasets', 'history'],
    ds3_paysim: ['overview', 'fraud', 'security', 'analytics', 'datasets', 'history'],
    ds4_baf: ['overview', 'fraud', 'datasets', 'history'],
  };
  return {
    manifest_version: 1, runtime_status: 'ready', dependencies: {},
    datasets: Object.entries(support).map(([dataset_id, tabs]) => ({
      dataset_id, allowed_modes: [dataset_id === 'live' ? 'operational' : 'benchmark'],
      ground_truth_available: dataset_id !== 'live',
      tab_availability: Object.fromEntries(['overview', 'fraud', 'security', 'analytics', 'datasets', 'history'].map(tab => [tab, {
        supported: tabs.includes(tab), available: tabs.includes(tab), required_dependencies: [], missing_dependencies: [],
        reason: tabs.includes(tab) ? null : (['security', 'analytics'].includes(tab) ? 'DS3 PaySim only' : 'Unsupported by dataset semantics'),
      }])),
    })),
  };
}

async function mockRunWorkspace(page, role = 'ADMIN', transitions = [], manifest = capabilityFixture()) {
  await page.route('**/api/auth/login', route => route.fulfill({
    status: 200, contentType: 'application/json',
    body: JSON.stringify({ access_token: browserToken(), role, username: role === 'ADMIN' ? 'admin' : 'analyst_1' }),
  }));
  await page.route('**/api/capabilities*', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(manifest) }));
  await page.route('**/api/datasets/**', route => route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }));
  await page.route('**/api/health/ready', route => route.fulfill({
    status: 200, contentType: 'application/json', body: JSON.stringify({
      status: 'ready', kafka: true, postgres: true, redis: true, neo4j: false,
      clickhouse: true, minio: true, live_ingestion: true,
      live_source: { status: 'idle', event_types_seen: [], last_event_at: null },
    }),
  }));
  await page.route('**/api/runs**', async route => {
    const request = route.request();
    const url = new URL(request.url());
    if (request.method() === 'POST' && url.pathname.endsWith('/transition')) {
      const body = request.postDataJSON(); transitions.push(body);
      const runId = url.pathname.split('/').at(-2);
      const run = runFixtures.find(item => item.run_id === runId);
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ...run, status: body.status, version: run.version + 1 }) });
    }
    const runId = url.pathname.split('/').at(-1);
    const run = runFixtures.find(item => item.run_id === runId);
    if (run) return route.fulfill({
      status: 200, contentType: 'application/json', body: JSON.stringify({
        ...run, contract_version: 1, evaluator_version: 'rules-v2', requested_start_offset: 0, requested_end_offset: 1000,
        offsets: [{ topic: 'benchmark-events', partition: 0, start_offset: 0, current_offset: 750, end_offset: 1000 }],
        counters: [{ counter_name: 'published', counter_value: 750 }],
        reconciliation: [{ check_id: 'check-1', classification: 'MISSING', store: 'CLICKHOUSE', metric: 'events', expected_count: 1000, actual_count: 990, discrepancy_count: 10, sample_ids: ['event-7'] }],
      }),
    });
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ total: runFixtures.length, page: 1, limit: 20, data: runFixtures }) });
  });
  await page.goto('/');
  await page.getByLabel('Username').fill(role === 'ADMIN' ? 'admin' : 'analyst_1');
  await page.getByLabel('Password').fill('mock-password');
  await page.getByRole('button', { name: 'Sign In' }).click();
  await expect(page.getByRole('heading', { name: 'Command Center', level: 1 })).toBeVisible();
  await page.getByRole('button', { name: 'Data Sources' }).click();
  await expect(page.getByRole('heading', { name: 'Data Runs', level: 2 })).toBeVisible();
}

async function login(page) {
  const password = process.env.E2E_PASSWORD || environment.DASHBOARD_ADMIN_PASSWORD;
  if (!password) throw new Error('Set E2E_PASSWORD or DASHBOARD_ADMIN_PASSWORD in the repository .env file');
  await page.goto('/');
  await page.getByLabel('Username').fill(process.env.E2E_USERNAME || 'admin');
  await page.getByLabel('Password').fill(password);
  await page.getByRole('button', { name: 'Sign In' }).click();
  await expect(page.getByRole('heading', { name: 'Command Center', level: 1 })).toBeVisible();
}

test('source context enforces mode and provenance boundaries', async ({ page }) => {
  await login(page);
  const source = page.getByLabel('Nguồn dữ liệu');
  const mode = page.getByLabel('Chế độ');
  const historyNavigation = page.getByRole('button', { name: /Historical Analytics/ });

  await expect(source).toHaveValue('live');
  await expect(mode).toHaveValue('operational');
  await expect(mode).toBeDisabled();
  await expect(page.getByText('External source · not configured')).toBeVisible();
  await expect(historyNavigation).toBeDisabled();
  await expect(historyNavigation).toHaveAttribute('title', 'Unsupported by dataset semantics');

  await source.selectOption('ds3_paysim');
  await expect(mode).toHaveValue('benchmark');
  await expect(mode).toBeDisabled();
  await expect(page.getByText('Synthetic public simulation')).toBeVisible();
  await expect(page.getByText('Ground-truth fraud')).toBeVisible();
  await expect(historyNavigation).toBeEnabled();

  await source.selectOption('ds1_creditcard');
  await expect(mode).toHaveValue('benchmark');
  await expect(historyNavigation).toBeEnabled();
  await source.selectOption('ds4_baf');
  await expect(mode).toHaveValue('benchmark');
  await expect(historyNavigation).toBeEnabled();
  await source.selectOption('ds3_paysim');

  await page.reload();
  await expect(source).toHaveValue('ds3_paysim');
  await expect(mode).toHaveValue('benchmark');

  await page.getByRole('button', { name: 'Data Sources' }).click();
  await expect(page.getByRole('heading', { name: 'Data Sources', level: 1 })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Dataset catalog', level: 2 })).toBeVisible();

  await source.selectOption('live');
  await expect(mode).toHaveValue('operational');
  await expect(page.getByText('Live source boundary')).toBeVisible();
  await expect(page.getByText('Hidden', { exact: true }).first()).toBeVisible();
});

test('authenticated analytics and architecture views render end to end', async ({ page }) => {
  await login(page);
  const source = page.getByLabel('Nguồn dữ liệu');
  await source.selectOption('ds3_paysim');

  await page.getByRole('button', { name: 'Historical Analytics' }).click();
  await expect(page.getByRole('heading', { name: 'Historical Analytics', level: 1 })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Volume and risk signal', level: 2 })).toBeVisible();

  await page.getByRole('button', { name: 'AML Network' }).click();
  await expect(page.getByRole('heading', { name: 'AML Network', level: 1 })).toBeVisible();
  await expect(page.getByLabel('Nguồn dữ liệu')).toHaveCount(0);
  await expect(page.getByRole('heading', { name: 'Transaction network', level: 2 })).toBeVisible();
  await expect(page.getByText('Graph database unavailable')).toHaveCount(0);

  await page.getByRole('button', { name: 'Architecture Map' }).click();
  await expect(page.getByRole('heading', { name: 'Kiến trúc Banking Data Platform', level: 1 })).toBeVisible();
  await expect(page.locator('.react-flow')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Realtime & Kafka' })).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByText('Kafka broker')).toBeVisible();
  await expect(page.getByText('Spark fraud engine')).toBeVisible();
  await expect(page.getByText('Benchmark processor')).toBeVisible();
  await expect(page.getByText('FastAPI backend')).toBeVisible();
  await expect(page.getByTestId('rf__node-live-ingestion').getByText('Live ingestion gateway', { exact: true })).toBeVisible();
  await page.getByTestId('rf__node-transfer-source').getByText('External / demo sources', { exact: true }).click();
  const componentDetail = page.getByRole('region', { name: 'Chi tiết thành phần' });
  await expect(componentDetail).toContainText('Nguồn bên ngoài hoặc live simulator gọi HTTP gateway.');
  await expect(componentDetail).toContainText(/Đã cấu hình|Đang nhận live events/);
  await expect(page.getByText(/HTTP payment \+ transfer · (idle|streaming)/)).toBeVisible();
  await componentDetail.getByRole('button', { name: 'Đóng chi tiết thành phần' }).click();
  await expect(componentDetail).toHaveCount(0);

  await page.getByRole('button', { name: 'Batch & DQ' }).click();
  await expect(page.getByRole('button', { name: 'Batch & DQ' })).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByText('Airflow')).toBeVisible();
  await expect(page.getByText('Spark master + worker')).toBeVisible();
  await expect(page.getByText('Batch + DQ jobs')).toBeVisible();

  await page.getByRole('button', { name: 'Serving & Ops' }).click();
  await expect(page.getByRole('button', { name: 'Serving & Ops' })).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByText('Kafka Exporter')).toBeVisible();
  await expect(page.getByText('Prometheus')).toBeVisible();
  await expect(page.getByText('Grafana')).toBeVisible();
  await expect(page.getByText('Debezium Connect')).toBeVisible();
  await expect(page.getByText('Apache Superset')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Metrics explorer' })).toHaveAttribute('href', 'http://localhost:9090');
  await expect(page.getByRole('link', { name: 'Operations charts' })).toHaveAttribute('href', 'http://localhost:3000');
  await expect(page.getByTestId('rf__node-live-ingestion').getByText('Live ingestion gateway', { exact: true })).toBeVisible();

  await page.getByRole('button', { name: 'Toàn bộ' }).click();
  await expect(page.getByRole('button', { name: 'Toàn bộ' })).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByText(/Toàn bộ topology; dùng các view chuyên biệt/)).toBeVisible();
  await expect(page.getByText(/Đường nối thể hiện integration contract trong code/)).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Runtime dependencies', level: 2 })).toBeVisible();
  await expect(page.locator('.service-health-card').filter({ hasText: 'Live Ingestion' })).toBeVisible();
});

test('Data Runs exposes the shared runtime vocabulary and detailed reconciliation states', async ({ page }) => {
  await mockRunWorkspace(page);
  for (const status of ['ready', 'idle', 'running', 'stale', 'degraded', 'failed', 'not_applicable']) {
    const indicator = page.locator(`[data-runtime-status="${status}"]`).first();
    await expect(indicator).toBeVisible();
    await expect(indicator).toHaveAttribute('aria-label', /.+/);
  }
  await page.locator('.run-id-button').first().click();
  await expect(page.getByRole('heading', { name: 'Offsets', level: 3 })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Count flow', level: 3 })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Reconciliation evidence', level: 3 })).toBeVisible();
  await expect(page.getByText('event-7')).toBeVisible();
});

test('dashboard navigation and status controls are keyboard reachable', async ({ page }) => {
  await mockRunWorkspace(page);
  const architecture = page.getByRole('button', { name: 'Architecture Map' });
  await architecture.focus();
  await expect(architecture).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(page.getByRole('heading', { name: 'Kiến trúc Banking Data Platform', level: 1 })).toBeVisible();
  const probes = page.getByRole('button', { name: 'Run probes' });
  await probes.focus();
  await expect(probes).toBeFocused();
  await expect(page.locator('[data-runtime-status="failed"]').first()).toHaveAttribute('role', 'status');
});

test('Data Runs applies pause, resume and confirmed cancel transitions for admins', async ({ page }) => {
  const transitions = [];
  await mockRunWorkspace(page, 'ADMIN', transitions);
  await page.getByRole('button', { name: /Pause run 11111111/ }).click();
  await expect.poll(() => transitions.map(item => item.status)).toContain('PAUSING');
  await page.getByRole('button', { name: /Resume run 44444444/ }).click();
  await expect.poll(() => transitions.map(item => item.status)).toContain('RUNNING');
  page.once('dialog', dialog => dialog.accept());
  await page.getByRole('button', { name: /Cancel run 11111111/ }).click();
  await expect.poll(() => transitions.map(item => item.status)).toContain('CANCELLING');
});

test('Data Runs keeps run controls read-only for analysts', async ({ page }) => {
  await mockRunWorkspace(page, 'ANALYST');
  await expect(page.getByText('Read-only · ADMIN required for run control')).toBeVisible();
  await expect(page.getByRole('button', { name: /Pause run/ })).toHaveCount(0);
  await expect(page.getByRole('button', { name: /Resume run/ })).toHaveCount(0);
  await expect(page.getByRole('button', { name: /Cancel run/ })).toHaveCount(0);
});

test('capability runtime failure disables the affected fixed tab with a reason', async ({ page }) => {
  const manifest = capabilityFixture();
  const ds3 = manifest.datasets.find(item => item.dataset_id === 'ds3_paysim');
  ds3.tab_availability.analytics.available = false;
  ds3.tab_availability.analytics.reason = 'Unavailable dependencies: neo4j';
  ds3.tab_availability.analytics.missing_dependencies = ['neo4j'];
  await mockRunWorkspace(page, 'ANALYST', [], manifest);
  const aml = page.getByRole('button', { name: /AML Network/ });
  await expect(aml).toBeDisabled();
  await expect(aml).toHaveAttribute('title', 'Unavailable dependencies: neo4j');
});
