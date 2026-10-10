import React, { createContext, useContext, useMemo, useState } from 'react';

export const DATASET_DEFINITIONS = {
  live: {
    id: 'live', label: 'Live / Production', shortLabel: 'Live', sourceKind: 'live_source',
    description: 'Dữ liệu vận hành từ payment và transfer source đã cấu hình.',
    timeSemantics: 'event timestamp', supports: ['streaming', 'alerts', 'cases'],
  },
  ds1_creditcard: {
    id: 'ds1_creditcard', label: 'DS1 — Card Fraud', shortLabel: 'DS1', sourceKind: 'anonymized_real',
    description: 'Benchmark giao dịch thẻ ẩn danh; các trường V1–V28 không phải danh tính khách hàng.',
    timeSemantics: 'giây tương đối từ quan sát đầu tiên', supports: ['benchmark', 'fraud-evaluation'],
  },
  ds3_paysim: {
    id: 'ds3_paysim', label: 'DS3 — PaySim', shortLabel: 'DS3', sourceKind: 'synthetic_simulation',
    description: 'Mô phỏng mobile-money; không đại diện cho khách hàng hoặc giao dịch thật.',
    timeSemantics: 'step mô phỏng theo giờ', supports: ['benchmark', 'fraud-evaluation', 'aml-graph'],
  },
  ds4_baf: {
    id: 'ds4_baf', label: 'DS4 — Account Opening Fraud', shortLabel: 'DS4', sourceKind: 'privacy_preserving_synthetic',
    description: 'Benchmark fraud khi mở tài khoản; đây là application data, không phải payment stream.',
    timeSemantics: 'month benchmark (0–7)', supports: ['benchmark', 'account-risk'],
  },
};

export const DASHBOARD_MODES = {
  operational: { id: 'operational', label: 'Operational', description: 'Theo dõi nguồn dữ liệu và alert đang chạy.' },
  benchmark: { id: 'benchmark', label: 'Benchmark / Evaluation', description: 'Đánh giá detection so với ground truth của dataset.' },
};

const STORAGE_KEY = 'banking-dashboard-context';
const DEFAULT_CONTEXT = { datasetId: 'live', mode: 'operational' };

function readInitialContext() {
  try {
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY));
    if (stored && DATASET_DEFINITIONS[stored.datasetId] && DASHBOARD_MODES[stored.mode]) return stored;
  } catch {
    // Ignore malformed browser storage and use a safe default.
  }
  return DEFAULT_CONTEXT;
}

const DatasetContext = createContext(null);

export function DatasetProvider({ children }) {
  const [context, setContext] = useState(readInitialContext);

  const updateContext = (nextContext) => {
    setContext(previous => {
      const next = { ...previous, ...nextContext };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      return next;
    });
  };

  const value = useMemo(() => ({
    ...context,
    dataset: DATASET_DEFINITIONS[context.datasetId],
    modeDefinition: DASHBOARD_MODES[context.mode],
    setDatasetId: datasetId => updateContext({ datasetId, mode: datasetId === 'live' ? 'operational' : 'benchmark' }),
    setMode: mode => updateContext({ mode }),
  }), [context]);

  return <DatasetContext.Provider value={value}>{children}</DatasetContext.Provider>;
}

export function useDatasetContext() {
  const value = useContext(DatasetContext);
  if (!value) throw new Error('useDatasetContext must be used inside DatasetProvider');
  return value;
}

