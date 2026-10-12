import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { AuthContext } from './AuthContext';
import {
  BOOTSTRAP_CAPABILITY_MANIFEST,
  canShowGroundTruth, DASHBOARD_MODES, DATASET_DEFINITIONS,
  datasetCapability, DEFAULT_DASHBOARD_CONTEXT, normalizeDashboardContext,
  tabCapability, validateCapabilityManifest,
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
  const { token } = useContext(AuthContext);
  const [context, setContext] = useState(readInitialContext);
  const [manifest, setManifest] = useState(BOOTSTRAP_CAPABILITY_MANIFEST);
  const [manifestLoading, setManifestLoading] = useState(Boolean(token));
  const [manifestError, setManifestError] = useState('');

  useEffect(() => {
    if (!token) {
      setManifest(BOOTSTRAP_CAPABILITY_MANIFEST);
      setManifestLoading(false);
      setManifestError('');
      return undefined;
    }
    const controller = new AbortController();
    setManifestLoading(true); setManifestError('');
    fetch(`${window._env_?.API_URL || 'http://localhost:8000'}/api/capabilities?version=1`, {
      headers: { Authorization: `Bearer ${token}` }, signal: controller.signal,
    })
      .then(response => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
      })
      .then(payload => {
        const accepted = validateCapabilityManifest(payload);
        setManifest(accepted);
        setContext(previous => {
          const normalized = normalizeDashboardContext(previous, accepted);
          localStorage.setItem(STORAGE_KEY, JSON.stringify(normalized));
          return normalized;
        });
      })
      .catch(error => {
        if (error.name !== 'AbortError') {
          setManifest(BOOTSTRAP_CAPABILITY_MANIFEST);
          setManifestError(`Capability manifest unavailable: ${error.message}`);
        }
      })
      .finally(() => { if (!controller.signal.aborted) setManifestLoading(false); });
    return () => controller.abort();
  }, [token]);

  const updateContext = (nextContext) => {
    setContext(previous => {
      const next = normalizeDashboardContext({ ...previous, ...nextContext }, manifest);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      return next;
    });
  };

  const value = useMemo(() => ({
    ...context,
    dataset: DATASET_DEFINITIONS[context.datasetId],
    capability: datasetCapability(context.datasetId, manifest),
    modeDefinition: DASHBOARD_MODES[context.mode],
    groundTruthVisible: canShowGroundTruth(context, manifest),
    manifest,
    manifestLoading,
    manifestError,
    tabCapability: (tabId, datasetId = context.datasetId) => tabCapability(datasetId, tabId, manifest),
    setDatasetId: datasetId => updateContext({ datasetId }),
    setMode: mode => updateContext({ mode }),
  }), [context, manifest, manifestError, manifestLoading]);

  return <DatasetContext.Provider value={value}>{children}</DatasetContext.Provider>;
}

export function useDatasetContext() {
  const value = useContext(DatasetContext);
  if (!value) throw new Error('useDatasetContext must be used inside DatasetProvider');
  return value;
}
