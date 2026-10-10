export const DATASET_DEFINITIONS = {
  live: {
    id: 'live', label: 'Live — Not configured', shortLabel: 'Live', sourceKind: 'live_source',
    provenanceLabel: 'External source · not configured',
    description: 'Nguồn payment/transfer bên ngoài chưa được cấu hình; chỉ hiển thị dữ liệu vận hành được gửi có chủ đích.',
    timeSemantics: 'event timestamp', supports: ['streaming', 'alerts', 'cases'],
  },
  ds1_creditcard: {
    id: 'ds1_creditcard', label: 'DS1 — Card Fraud', shortLabel: 'DS1', sourceKind: 'anonymized_real',
    provenanceLabel: 'Anonymized public benchmark',
    description: 'Benchmark giao dịch thẻ ẩn danh; các trường V1–V28 không phải danh tính khách hàng.',
    timeSemantics: 'giây tương đối từ quan sát đầu tiên', supports: ['benchmark', 'fraud-evaluation'],
  },
  ds3_paysim: {
    id: 'ds3_paysim', label: 'DS3 — PaySim', shortLabel: 'DS3', sourceKind: 'synthetic_simulation',
    provenanceLabel: 'Synthetic public simulation',
    description: 'Mô phỏng mobile-money; không đại diện cho khách hàng hoặc giao dịch thật.',
    timeSemantics: 'step mô phỏng theo giờ', supports: ['benchmark', 'fraud-evaluation', 'aml-graph'],
  },
  ds4_baf: {
    id: 'ds4_baf', label: 'DS4 — Account Opening Fraud', shortLabel: 'DS4', sourceKind: 'privacy_preserving_synthetic',
    provenanceLabel: 'Privacy-preserving synthetic benchmark',
    description: 'Benchmark fraud khi mở tài khoản; đây là application data, không phải payment stream.',
    timeSemantics: 'month benchmark (0–7)', supports: ['benchmark', 'account-risk'],
  },
};

export const DASHBOARD_MODES = {
  operational: { id: 'operational', label: 'Operational', description: 'Theo dõi nguồn dữ liệu và alert đang chạy.' },
  benchmark: { id: 'benchmark', label: 'Benchmark / Evaluation', description: 'Đánh giá detection so với ground truth của dataset.' },
};

export const DATASET_MODE_MATRIX = {
  live: ['operational'],
  ds1_creditcard: ['benchmark'],
  ds3_paysim: ['benchmark'],
  ds4_baf: ['benchmark'],
};

export const DEFAULT_DASHBOARD_CONTEXT = Object.freeze({ datasetId: 'live', mode: 'operational' });

export const FIXED_TAB_DATASETS = Object.freeze({
  security: 'ds3_paysim',
  analytics: 'ds3_paysim',
});

export function fixedDatasetForTab(tabId) {
  return FIXED_TAB_DATASETS[tabId] || null;
}

export function allowedModesForDataset(datasetId) {
  return DATASET_MODE_MATRIX[datasetId] || DATASET_MODE_MATRIX.live;
}

export function normalizeDashboardContext(candidate = {}) {
  const datasetId = DATASET_DEFINITIONS[candidate?.datasetId] ? candidate.datasetId : DEFAULT_DASHBOARD_CONTEXT.datasetId;
  const allowedModes = allowedModesForDataset(datasetId);
  const mode = allowedModes.includes(candidate?.mode) ? candidate.mode : allowedModes[0];
  return { datasetId, mode };
}

export function canShowGroundTruth(context) {
  const normalized = normalizeDashboardContext(context);
  return normalized.datasetId !== 'live' && normalized.mode === 'benchmark';
}
