import React from 'react';
import { Sankey, Tooltip, ResponsiveContainer, FunnelChart, Funnel, LabelList } from 'recharts';

export default function AnalyticsTab({ sankeyData, funnelData }) {
  return (
    <div className="grid">
      <div className="panel col-span-6" style={{height: '400px'}}>
        <h2 className="panel-title">Money Flow Analysis (Sankey Diagram)</h2>
        <ResponsiveContainer width="100%" height={350}>
          <Sankey
            data={sankeyData}
            nodePadding={50}
            margin={{ top: 20, right: 20, bottom: 20, left: 20 }}
            link={{ stroke: '#77c878', strokeWidth: '10' }}
            node={{ stroke: '#141a28', strokeWidth: '2' }}
          >
            <Tooltip 
              contentStyle={{backgroundColor: '#141a28', border: 'none', borderRadius: '8px'}} 
              itemStyle={{color: '#fff'}} 
            />
          </Sankey>
        </ResponsiveContainer>
      </div>

      <div className="panel col-span-6" style={{height: '400px'}}>
        <h2 className="panel-title">Transaction Pipeline Health (Funnel)</h2>
        <ResponsiveContainer width="100%" height={350}>
          <FunnelChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
            <Tooltip 
              contentStyle={{backgroundColor: '#141a28', border: 'none', borderRadius: '8px'}} 
              itemStyle={{color: '#fff'}} 
            />
            <Funnel
              dataKey="value"
              data={funnelData}
              isAnimationActive
            >
              <LabelList position="right" fill="#fff" stroke="none" dataKey="name" />
            </Funnel>
          </FunnelChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
