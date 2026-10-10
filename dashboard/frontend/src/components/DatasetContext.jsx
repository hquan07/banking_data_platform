import React, { createContext, useContext, useMemo, useState } from 'react';
import {
  canShowGroundTruth, DASHBOARD_MODES, DATASET_DEFINITIONS,
  DEFAULT_DASHBOARD_CONTEXT, normalizeDashboardContext,
} from '../datasetContextContract';

export { DASHBOARD_MODES, DATASET_DEFINITIONS } from '../datasetContextContract';

const STORAGE_KEY = 'banking-dashboard-context';

function readInitialContext() {
  try {
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY));
    return normalizeDashboardContext(stored);
  } catch {
    // Ignore malformed browser storage and use a safe default.
  }
  return DEFAULT_DASHBOARD_CONTEXT;
}

const DatasetContext = createContext(null);

export function DatasetProvider({ children }) {
  const [context, setContext] = useState(readInitialContext);

  const updateContext = (nextContext) => {
    setContext(previous => {
      const next = normalizeDashboardContext({ ...previous, ...nextContext });
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      return next;
    });
  };

  const value = useMemo(() => ({
    ...context,
    dataset: DATASET_DEFINITIONS[context.datasetId],
    modeDefinition: DASHBOARD_MODES[context.mode],
    groundTruthVisible: canShowGroundTruth(context),
    setDatasetId: datasetId => updateContext({ datasetId }),
    setMode: mode => updateContext({ mode }),
  }), [context]);

  return <DatasetContext.Provider value={value}>{children}</DatasetContext.Provider>;
}

export function useDatasetContext() {
  const value = useContext(DatasetContext);
  if (!value) throw new Error('useDatasetContext must be used inside DatasetProvider');
  return value;
}
