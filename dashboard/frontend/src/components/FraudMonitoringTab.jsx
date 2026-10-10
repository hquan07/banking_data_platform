import React from 'react';
import { PageHeader, Panel, StateMessage } from './ui';
import { useDatasetContext } from './DatasetContext';

export default function FraudMonitoringTab() {
  const { dataset } = useDatasetContext();
  return <div className="page-stack"><PageHeader eyebrow="Detection analytics" title="Fraud Monitor" description={`Phân tích detection theo ngữ nghĩa của ${dataset.label}.`} /><Panel title="Đang chuẩn bị phân tích" className="col-span-12"><StateMessage>Biểu đồ fraud theo dataset sẽ được nối với API analytics ở phần kế tiếp.</StateMessage></Panel></div>;
}

