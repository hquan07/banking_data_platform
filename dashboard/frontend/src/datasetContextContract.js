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

export const DEFAULT_DASHBOARD_CONTEXT = Object.freeze({ datasetId: 'live', mode: 'operational' });

const workspaceTabs = ['overview', 'fraud', 'security', 'analytics', 'datasets', 'history'];
const bootstrapSupport = {
  live: ['overview', 'fraud', 'datasets'],
  ds1_creditcard: ['overview', 'fraud', 'datasets', 'history'],
  ds3_paysim: workspaceTabs,
  ds4_baf: ['overview', 'fraud', 'datasets', 'history'],
};

export const BOOTSTRAP_CAPABILITY_MANIFEST = Object.freeze({
  manifest_version: 1,
  source: 'bootstrap',
  datasets: Object.keys(DATASET_DEFINITIONS).map(datasetId => ({
    dataset_id: datasetId,
    allowed_modes: [datasetId === 'live' ? 'operational' : 'benchmark'],
    ground_truth_available: datasetId !== 'live',
    graph_support: datasetId === 'ds3_paysim',
    case_support: datasetId === 'ds3_paysim',
    tab_availability: Object.fromEntries(workspaceTabs.map(tabId => {
      const supported = bootstrapSupport[datasetId].includes(tabId);
      return [tabId, {
        supported, available: supported, required_dependencies: [], missing_dependencies: [],
        reason: supported ? null : (['security', 'analytics'].includes(tabId) ? 'DS3 PaySim only' : 'Unsupported by dataset semantics'),
      }];
    })),
  })),
});

export function validateCapabilityManifest(candidate) {
  if (candidate?.manifest_version !== 1 || !Array.isArray(candidate?.datasets)) {
    throw new Error('Unsupported dashboard capability manifest');
  }
  const ids = new Set(candidate.datasets.map(item => item.dataset_id));
  if (!Object.keys(DATASET_DEFINITIONS).every(datasetId => ids.has(datasetId))) {
    throw new Error('Capability manifest is missing a dashboard dataset');
  }
  return candidate;
}

export function datasetCapability(datasetId, manifest = BOOTSTRAP_CAPABILITY_MANIFEST) {
  return manifest.datasets.find(item => item.dataset_id === datasetId)
    || BOOTSTRAP_CAPABILITY_MANIFEST.datasets.find(item => item.dataset_id === datasetId)
    || BOOTSTRAP_CAPABILITY_MANIFEST.datasets[0];
}

export function tabCapability(datasetId, tabId, manifest = BOOTSTRAP_CAPABILITY_MANIFEST) {
  return datasetCapability(datasetId, manifest).tab_availability?.[tabId]
    || { supported: true, available: true, required_dependencies: [], missing_dependencies: [], reason: null };
}

export function fixedDatasetForTab(tabId, manifest = BOOTSTRAP_CAPABILITY_MANIFEST) {
  const candidates = manifest.datasets.filter(item => item.tab_availability?.[tabId]?.supported);
  return candidates.length === 1 ? candidates[0].dataset_id : null;
}

export function allowedModesForDataset(datasetId, manifest = BOOTSTRAP_CAPABILITY_MANIFEST) {
  return datasetCapability(datasetId, manifest).allowed_modes;
}

export function normalizeDashboardContext(candidate = {}, manifest = BOOTSTRAP_CAPABILITY_MANIFEST) {
  const datasetId = DATASET_DEFINITIONS[candidate?.datasetId] ? candidate.datasetId : DEFAULT_DASHBOARD_CONTEXT.datasetId;
  const allowedModes = allowedModesForDataset(datasetId, manifest);
  const mode = allowedModes.includes(candidate?.mode) ? candidate.mode : allowedModes[0];
  return { datasetId, mode };
}

export function canShowGroundTruth(context, manifest = BOOTSTRAP_CAPABILITY_MANIFEST) {
  const normalized = normalizeDashboardContext(context, manifest);
  return datasetCapability(normalized.datasetId, manifest).ground_truth_available
    && normalized.mode === 'benchmark';
}
