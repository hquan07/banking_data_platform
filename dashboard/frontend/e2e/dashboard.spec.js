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

  await expect(source).toHaveValue('live');
  await expect(mode).toHaveValue('operational');
  await expect(mode).toBeDisabled();
  await expect(page.getByText('External source · not configured')).toBeVisible();

  await source.selectOption('ds3_paysim');
  await expect(mode).toHaveValue('benchmark');
  await expect(mode).toBeDisabled();
  await expect(page.getByText('Synthetic public simulation')).toBeVisible();
  await expect(page.getByText('Ground-truth fraud')).toBeVisible();

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
  await page.getByText('Live event sources', { exact: true }).click();
  const componentDetail = page.getByRole('region', { name: 'Chi tiết thành phần' });
  await expect(componentDetail).toContainText('Chưa có nguồn payment-events hoặc transfer-events bên ngoài được kết nối.');
  await expect(componentDetail).toContainText('Chưa tích hợp');
  await expect(page.getByText('payment + transfer · chưa cấu hình')).toBeVisible();
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

  await page.getByRole('button', { name: 'Toàn bộ' }).click();
  await expect(page.getByRole('button', { name: 'Toàn bộ' })).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByText(/Toàn bộ topology; dùng các view chuyên biệt/)).toBeVisible();
  await expect(page.getByText(/Đường nối thể hiện integration contract trong code/)).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Runtime dependencies', level: 2 })).toBeVisible();
});
