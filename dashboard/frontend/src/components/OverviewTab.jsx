import React from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export default function OverviewTab({ data }) {
  return (
    <div className="grid">
      <div className="panel col-span-12">
        <h2 className="panel-title">Giá trị thanh toán nhận qua luồng sự kiện</h2>
        {data.length === 0 ? (
          <div role="status" style={{height: 300, display: 'grid', placeItems: 'center', color: '#94a3b8'}}>
            Chưa có sự kiện thanh toán từ nguồn dữ liệu.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={data}>
              <defs>
                <linearGradient id="colorAmount" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" vertical={false} />
              <XAxis dataKey="time" stroke="rgba(255,255,255,0.5)" tick={{fill: 'rgba(255,255,255,0.5)', fontSize: 12}} />
              <YAxis stroke="rgba(255,255,255,0.5)" tick={{fill: 'rgba(255,255,255,0.5)', fontSize: 12}} />
              <Tooltip
                contentStyle={{backgroundColor: 'rgba(20, 26, 40, 0.9)', borderColor: 'rgba(255,255,255,0.1)', borderRadius: '8px'}}
                itemStyle={{color: '#fff'}}
              />
              <Area type="monotone" dataKey="amount" stroke="#3b82f6" strokeWidth={2} fillOpacity={1} fill="url(#colorAmount)" isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
