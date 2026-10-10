import { useContext, useEffect, useState } from 'react';
import { AuthContext } from './AuthContext';
import { useDatasetContext } from './DatasetContext';

const EMPTY = { overview: null, timeseries: [], segments: {} };

export function useDatasetAnalytics() {
  const { token } = useContext(AuthContext);
  const { datasetId } = useDatasetContext();
  const [state, setState] = useState({ ...EMPTY, loading: datasetId !== 'live', error: '' });

  useEffect(() => {
    if (datasetId === 'live') {
      setState({ ...EMPTY, loading: false, error: '' });
      return undefined;
    }
    const controller = new AbortController();
    const baseUrl = window._env_?.API_URL || 'http://localhost:8000';
    setState(previous => ({ ...previous, loading: true, error: '' }));
    Promise.all(['overview', 'timeseries', 'segments'].map(async endpoint => {
      const response = await fetch(`${baseUrl}/api/datasets/${datasetId}/${endpoint}`, {
        headers: { Authorization: `Bearer ${token}` }, signal: controller.signal,
      });
      if (response.status === 401) throw new Error('Phiên đăng nhập đã hết hạn. Hãy đăng nhập lại.');
      if (!response.ok) throw new Error(`Không tải được ${endpoint} (${response.status})`);
      return response.json();
    }))
      .then(([overview, timeseries, segmentPayload]) => setState({ overview, timeseries, segments: segmentPayload.segments || {}, loading: false, error: '' }))
      .catch(error => { if (error.name !== 'AbortError') setState({ ...EMPTY, loading: false, error: error.message }); });
    return () => controller.abort();
  }, [datasetId, token]);

  return state;
}

