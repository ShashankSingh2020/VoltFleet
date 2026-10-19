import React from 'react';
import { MapContainer, TileLayer, Marker, Popup, Circle, Polyline } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

// Custom Map Marker using Leaflet DivIcon
const createVehiclePin = (status, isThermalSpike) => {
  const bg = isThermalSpike ? '#e11d48' : status === 'AVAILABLE' ? '#10b981' : '#38bdf8';
  return L.divIcon({
    className: 'custom-fleet-marker',
    html: `<div style="background-color: ${bg}; width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; border: 2px solid #ffffff; box-shadow: 0 0 12px ${bg}; cursor: pointer;">
             <div style="width: 8px; height: 8px; background: white; border-radius: 50%;"></div>
           </div>`,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  });
};

export default function FleetMap({ vehicles = [], telemetryHistory = [], depotLocation = [37.7749, -122.4194] }) {
  // Breadcrumb path coordinates
  const breadcrumbCoords = telemetryHistory
    .filter(pt => pt.latitude && pt.longitude)
    .map(pt => [pt.latitude, pt.longitude]);

  return (
    <div className="bg-fleet-900 border border-fleet-800 rounded-xl p-5 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-base font-semibold text-white">Live Geospatial Telematics & Depot Geofence</h3>
          <p className="text-xs text-slate-400">Real-time GPS positions streamed over WebSockets</p>
        </div>
        <div className="flex items-center gap-3 text-xs">
          <span className="flex items-center gap-1.5 text-slate-300">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span> Available
          </span>
          <span className="flex items-center gap-1.5 text-slate-300">
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-400"></span> In Transit
          </span>
          <span className="flex items-center gap-1.5 text-slate-300">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500 animate-pulse"></span> Thermal Alert (&gt;45°C)
          </span>
        </div>
      </div>

      <div className="h-[460px] w-full rounded-lg overflow-hidden border border-fleet-800 relative z-0">
        <MapContainer
          center={depotLocation}
          zoom={13}
          scrollWheelZoom={false}
          className="h-full w-full"
        >
          {/* Dark Basemap */}
          <TileLayer
            attribution='&copy; <a href="https://carto.com/">CARTO</a>'
            url="https://{s}.basemaps.cartocdn.com/rastertiles/dark_all/{z}/{x}/{y}{r}.png"
          />

          {/* North Depot Geofence (1200 meter radius) */}
          <Circle
            center={depotLocation}
            radius={1200}
            pathOptions={{ color: '#06b6d4', fillColor: '#0891b2', fillOpacity: 0.15, dashArray: '6, 6' }}
          >
            <Popup className="text-xs">
              <strong>North Depot Hub</strong><br />
              Geofence Radius: 1.2 km<br />
              Grid Interconnect: 400.0 kW
            </Popup>
          </Circle>

          {/* Live GPS Breadcrumbs */}
          {breadcrumbCoords.length > 1 && (
            <Polyline
              positions={breadcrumbCoords}
              pathOptions={{ color: '#38bdf8', weight: 3, opacity: 0.7 }}
            />
          )}

          {/* Vehicle Markers */}
          {vehicles.map((v) => {
            const lat = Number(v.last_latitude) || depotLocation[0];
            const lng = Number(v.last_longitude) || depotLocation[1];
            const isSpike = parseFloat(v.battery_temperature_celsius || 30) > 45;

            return (
              <Marker
                key={v.id}
                position={[lat, lng]}
                icon={createVehiclePin(v.status, isSpike)}
              >
                <Popup className="text-xs">
                  <div className="space-y-1">
                    <strong>{v.license_plate}</strong> ({v.nickname || 'Fleet Vehicle'})<br />
                    <span>Status: {v.status}</span><br />
                    <span>SoC: {v.current_soc_percent}%</span><br />
                    <span>Temp: {v.battery_temperature_celsius || 32.0} °C</span><br />
                    <span>Speed: {v.speed_kmh || 0} km/h</span>
                  </div>
                </Popup>
              </Marker>
            );
          })}
        </MapContainer>
      </div>
    </div>
  );
}
