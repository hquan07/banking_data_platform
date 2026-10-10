import React from 'react';
import { Database, Info } from 'lucide-react';
import { DATASET_DEFINITIONS, DASHBOARD_MODES, useDatasetContext } from './DatasetContext';
import { allowedModesForDataset } from '../datasetContextContract';

export default function DatasetContextBar() {
  const { datasetId, mode, dataset, modeDefinition, setDatasetId, setMode } = useDatasetContext();
  const availableModes = allowedModesForDataset(datasetId).map(modeId => DASHBOARD_MODES[modeId]);

  return (
    <section className="dataset-context-bar" aria-label="Dashboard data context">
      <div className="dataset-context-controls">
        <label>
          <span>Nguồn dữ liệu</span>
          <select value={datasetId} onChange={event => setDatasetId(event.target.value)}>
            {Object.values(DATASET_DEFINITIONS).map(item => <option key={item.id} value={item.id}>{item.label}</option>)}
          </select>
        </label>
        <label>
          <span>Chế độ</span>
          <select value={mode} onChange={event => setMode(event.target.value)} disabled={availableModes.length === 1}>
            {availableModes.map(item => <option key={item.id} value={item.id}>{item.label}</option>)}
          </select>
        </label>
      </div>
      <div className="dataset-context-provenance">
        <div className="dataset-context-title">
          <Database size={17} /><strong>{dataset.label}</strong>
          <span className={`context-mode context-mode-${mode}`}>{modeDefinition.label}</span>
          <span className="context-source-kind">{dataset.provenanceLabel}</span>
        </div>
        <div className="dataset-context-details">
          <span><Info size={14} /> {dataset.description}</span>
          <span>Time: {dataset.timeSemantics}</span>
        </div>
      </div>
    </section>
  );
}
