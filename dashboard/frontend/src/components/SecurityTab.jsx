import React from 'react';
import { PieChart, Pie, Cell, ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';
import ForceGraph2D from 'react-force-graph-2d';
import { ShieldAlert } from 'lucide-react';

const COLORS = ['#ef4444', '#f59e0b', '#3b82f6'];

export default function SecurityTab({ alerts, graphData, scatterData, riskyAccountsData, donutData }) {
  return (
    <div className="grid">
      {/* Alert Feed */}
      <div className="panel col-span-4">
        <h2 className="panel-title">Security Alerts</h2>
        <div className="alert-feed">
          {alerts.length === 0 ? (
            <div className="text-secondary" style={{textAlign: 'center', marginTop: '2rem'}}>No alerts detected.</div>
          ) : (
            alerts.map((alert, i) => (
              <div key={i} className="alert-card slide-in">
                <div style={{display: 'flex', justifyContent: 'space-between'}}>
                  <span style={{color: '#f59e0b', fontWeight: '600', fontSize: '12px'}}>{alert.rule}</span>
                  <span style={{color: 'var(--text-secondary)', fontSize: '12px'}}>Just now</span>
                </div>
                <div style={{marginTop: '4px', fontSize: '14px'}}>
                  Account: <strong>{alert.account_id}</strong>
                </div>
                <div style={{marginTop: '2px', fontSize: '14px'}}>
                  Amount: ${alert.amount} | Risk: {alert.risk_score}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Fraud Distribution */}
      <div className="panel col-span-4">
        <h2 className="panel-title">Fraud Distribution</h2>
        <ResponsiveContainer width="100%" height={250}>
          <PieChart>
            <Pie data={donutData} innerRadius={60} outerRadius={80} paddingAngle={5} dataKey="value">
              {donutData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <RechartsTooltip 
              contentStyle={{backgroundColor: '#141a28', border: 'none', borderRadius: '8px'}} 
              itemStyle={{color: '#fff'}} 
            />
          </PieChart>
        </ResponsiveContainer>
      </div>

      {/* Top Risky Accounts */}
      <div className="panel col-span-4">
        <h2 className="panel-title">Top Risky Accounts</h2>
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={riskyAccountsData} layout="vertical" margin={{top: 5, right: 30, left: 20, bottom: 5}}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" horizontal={false} />
            <XAxis type="number" stroke="rgba(255,255,255,0.5)" />
            <YAxis dataKey="name" type="category" stroke="rgba(255,255,255,0.5)" width={80} />
            <RechartsTooltip 
              contentStyle={{backgroundColor: '#141a28', border: 'none', borderRadius: '8px'}} 
              itemStyle={{color: '#fff'}} 
              cursor={{fill: 'rgba(255,255,255,0.05)'}}
            />
            <Bar dataKey="score" fill="#ef4444" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* AML Graph */}
      <div className="panel col-span-6" style={{height: '350px'}}>
        <h2 className="panel-title">AML Network Graph (Neo4j)</h2>
        <div style={{height: '100%', borderRadius: '8px', overflow: 'hidden'}}>
          <ForceGraph2D
            graphData={graphData}
            width={600}
            height={300}
            nodeAutoColorBy="group"
            nodeLabel="id"
            backgroundColor="rgba(20, 26, 40, 0)"
            linkColor={() => 'rgba(255,255,255,0.2)'}
            linkDirectionalArrowLength={3.5}
            linkDirectionalArrowRelPos={1}
            nodeRelSize={6}
          />
        </div>
      </div>

      {/* Anomaly Scatter Plot */}
      <div className="panel col-span-6" style={{height: '350px'}}>
        <h2 className="panel-title">Anomaly Detection (Scatter Plot)</h2>
        <ResponsiveContainer width="100%" height={300}>
          <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
            <XAxis dataKey="x" type="number" name="Time" stroke="rgba(255,255,255,0.5)" domain={['dataMin', 'dataMax']} tick={false} />
            <YAxis dataKey="y" type="number" name="Amount" stroke="rgba(255,255,255,0.5)" />
            <RechartsTooltip 
              cursor={{ strokeDasharray: '3 3' }} 
              contentStyle={{backgroundColor: '#141a28', border: 'none', borderRadius: '8px'}} 
              itemStyle={{color: '#fff'}} 
            />
            <Scatter name="Transactions" data={scatterData} fill="#3b82f6">
              {scatterData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.isAnomaly ? '#ef4444' : '#3b82f6'} />
              ))}
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
