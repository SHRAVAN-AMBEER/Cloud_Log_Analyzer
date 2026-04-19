import React from 'react';
import {
  ComposableMap,
  Geographies,
  Geography,
  Marker
} from 'react-simple-maps';

const geoUrl = "https://unpkg.com/world-atlas@2.0.2/countries-110m.json";

export const ThreatMap = ({ alerts }) => {
  // Extract coordinates from alerts
  const markers = alerts
    .filter(alert => alert.latitude !== undefined && alert.longitude !== undefined)
    .map(alert => ({
      name: alert.user_id,
      coordinates: [alert.longitude, alert.latitude],
      risk: alert.risk_level
    }));

  return (
    <div className="chart-panel" style={{ minHeight: '400px' }}>
      <h2>Global Threat Origins</h2>
      <div className="chart-wrapper" style={{ display: 'flex', justifyContent: 'center' }}>
        <ComposableMap
          projectionConfig={{ scale: 140 }}
          style={{ width: "100%", height: "100%" }}
        >
          <Geographies geography={geoUrl}>
            {({ geographies }) =>
              geographies.map(geo => (
                <Geography
                  key={geo.rsmKey}
                  geography={geo}
                  fill="rgba(148, 163, 184, 0.1)"
                  stroke="rgba(148, 163, 184, 0.2)"
                  strokeWidth={0.5}
                  style={{
                    hover: { fill: "rgba(59, 130, 246, 0.2)", outline: "none" },
                    pressed: { fill: "rgba(59, 130, 246, 0.4)", outline: "none" },
                    default: { outline: "none" }
                  }}
                />
              ))
            }
          </Geographies>

          {markers.map((marker, idx) => (
            <Marker key={idx} coordinates={marker.coordinates}>
              <circle 
                r={6} 
                fill={marker.risk === 'CRITICAL' || marker.risk === 'HIGH' ? "rgba(239, 68, 68, 0.8)" : "rgba(234, 179, 8, 0.8)"} 
                stroke="#fff" 
                strokeWidth={1} 
              />
              <circle 
                r={14} 
                fill={marker.risk === 'CRITICAL' || marker.risk === 'HIGH' ? "rgba(239, 68, 68, 0.3)" : "rgba(234, 179, 8, 0.3)"} 
                style={{ animation: 'pulse 2s infinite' }}
              />
            </Marker>
          ))}
        </ComposableMap>
      </div>
    </div>
  );
};
