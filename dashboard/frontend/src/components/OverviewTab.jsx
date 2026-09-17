import React from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { ComposableMap, Geographies, Geography, Marker } from "react-simple-maps";

const geoUrl = "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json";

export default function OverviewTab({ data, mapData }) {
  return (
    <div className="grid">
      <div className="panel col-span-12">
        <h2 className="panel-title">Real-time Transaction Volume (TPS)</h2>
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
      </div>

      <div className="panel col-span-12">
        <h2 className="panel-title">Geographic Activity Heatmap (Vietnam / Southeast Asia)</h2>
        <div style={{height: '400px', width: '100%', display: 'flex', justifyContent: 'center', overflow: 'hidden', borderRadius: '8px'}}>
          <ComposableMap
            projection="geoMercator"
            projectionConfig={{
              scale: 1200,
              center: [106, 16] // Center on Vietnam
            }}
            width={800}
            height={400}
            style={{ width: "100%", height: "100%" }}
          >
            <Geographies geography={geoUrl}>
              {({ geographies }) =>
                geographies.map((geo) => (
                  <Geography
                    key={geo.rsmKey}
                    geography={geo}
                    fill="rgba(255, 255, 255, 0.05)"
                    stroke="rgba(255, 255, 255, 0.1)"
                    style={{
                      default: { outline: "none" },
                      hover: { fill: "rgba(255, 255, 255, 0.1)", outline: "none" },
                      pressed: { outline: "none" },
                    }}
                  />
                ))
              }
            </Geographies>
            {mapData.map((marker, i) => (
              <Marker key={i} coordinates={[marker.lng, marker.lat]}>
                <circle r={4} fill="#3b82f6" style={{animation: 'pulse 1.5s infinite'}} />
              </Marker>
            ))}
          </ComposableMap>
        </div>
      </div>
    </div>
  );
}
