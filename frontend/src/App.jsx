import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import OverviewTab from './components/dashboard/OverviewTab';
import VehiclesTab from './components/vehicles/VehiclesTab';
import ChargingTab from './components/charging/ChargingTab';
import AnomaliesTab from './components/anomalies/AnomaliesTab';
import AiChatTab from './components/ai/AiChatTab';
import FleetMap from './components/map/FleetMap';
import { api } from './services/api';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [isOnline, setIsOnline] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);
  const [summary, setSummary] = useState(null);
  const [vehicles, setVehicles] = useState([]);
  const [anomalies, setAnomalies] = useState([]);
  const [plans, setPlans] = useState([]);
  const [telemetryHistory, setTelemetryHistory] = useState([
    { latitude: 37.7749, longitude: -122.4194 },
    { latitude: 37.7780, longitude: -122.4150 },
    { latitude: 37.7810, longitude: -122.4100 },
  ]);

  const loadData = async () => {
    try {
      await api.login();
      const [sum, veh, anom, pln] = await Promise.all([
        api.getFleetSummary().catch(() => null),
        api.getVehicles().catch(() => ({ results: [] })),
        api.getAnomalies().catch(() => ({ results: [] })),
        api.getChargingPlans().catch(() => ({ results: [] })),
      ]);

      if (sum) {
        setSummary(sum);
        setVehicles(veh.results || []);
        setAnomalies(anom.results || []);
        setPlans(pln.results || []);
        setIsOnline(true);
      }
    } catch (err) {
      console.warn('Backend login fallback to mock:', err);
      setIsOnline(false);
      setSummary({
        total_vehicles: 2,
        average_soc_percent: '45.10',
        total_distance_km: '46.20',
        total_energy_kwh: '38.50',
        average_efficiency_kwh_per_100km: '83.33',
      });
      setVehicles([
        { id: '1', license_plate: 'APEX-EV-01', nickname: 'Metro Van Alpha', current_soc_percent: '35.0', odometer_km: '14250.0', status: 'AVAILABLE', vin: '1V9APEX0000000001', last_latitude: 37.7749, last_longitude: -122.4194, battery_temperature_celsius: 52.5 },
        { id: '2', license_plate: 'APEX-EV-02', nickname: 'Heavy Transport Beta', current_soc_percent: '22.0', odometer_km: '28400.0', status: 'IN_TRANSIT', vin: '1V9APEX0000000002', last_latitude: 37.7820, last_longitude: -122.4080, battery_temperature_celsius: 31.5 },
      ]);
      setAnomalies([
        { id: '777375ee-a3fa-405e-8e7d-82c82b8ee8a0', vehicle_plate: 'APEX-EV-01', anomaly_type: 'HIGH_BATTERY_TEMP', severity: 'CRITICAL', status: 'OPEN', observed_value: '52.50 °C', threshold_value: '> 45.0 °C', evidence_summary: 'Battery core temperature reached 52.50 °C.' }
      ]);
    }
  };

  useEffect(() => {
    loadData();

    // Connect to Django Channels WebSocket for real-time telemetry streaming
    const wsUrl = 'ws://127.0.0.1:8000/ws/telemetry/';
    const socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      console.log('Connected to VoltFleet WebSocket channel');
      setWsConnected(true);
    };

    socket.onmessage = (event) => {
      try {
        const livePoint = JSON.parse(event.data);
        setVehicles((prev) =>
          prev.map((v) =>
            v.id === livePoint.vehicle_id || v.license_plate === livePoint.vehicle_plate
              ? {
                  ...v,
                  current_soc_percent: livePoint.soc_percent,
                  battery_temperature_celsius: livePoint.battery_temperature_celsius,
                  last_latitude: livePoint.latitude,
                  last_longitude: livePoint.longitude,
                  speed_kmh: livePoint.speed_kmh,
                }
              : v
          )
        );

        setTelemetryHistory((prev) => [...prev.slice(-30), livePoint]);

        // Auto-refresh summary
        api.getFleetSummary().then((data) => setSummary(data)).catch(() => {});
      } catch (e) {
        console.error('Error parsing live telemetry:', e);
      }
    };

    socket.onclose = () => {
      setWsConnected(false);
    };

    socket.onerror = (err) => {
      console.warn('WebSocket connection error:', err);
      setWsConnected(false);
    };

    return () => socket.close();
  }, []);

  return (
    <div className="min-h-screen bg-fleet-950 text-slate-100 flex flex-col">
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        anomalyCount={anomalies.filter((a) => a.status === 'OPEN').length}
        isOnline={isOnline}
      />

      {/* Real-time WebSocket connection strip */}
      <div className="bg-fleet-900 border-b border-fleet-800 px-4 py-1 text-xs flex justify-between items-center text-slate-400">
        <span className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`} />
          {wsConnected ? 'WebSocket Channel: ws://127.0.0.1:8000/ws/telemetry/ (Streaming)' : 'WebSocket Channel: Standby / Polling Fallback'}
        </span>
        <span className="hidden sm:inline font-mono">Channel Group: fleet_telemetry_broadcast</span>
      </div>

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {activeTab === 'dashboard' && (
          <>
            <OverviewTab
              summary={summary}
              anomalies={anomalies}
              vehicles={vehicles}
              setActiveTab={setActiveTab}
            />
            <FleetMap
              vehicles={vehicles}
              telemetryHistory={telemetryHistory}
            />
          </>
        )}
        {activeTab === 'vehicles' && (
          <>
            <VehiclesTab vehicles={vehicles} refreshData={loadData} />
            <FleetMap
              vehicles={vehicles}
              telemetryHistory={telemetryHistory}
            />
          </>
        )}
        {activeTab === 'charging' && (
          <ChargingTab plans={plans} refreshData={loadData} />
        )}
        {activeTab === 'anomalies' && (
          <AnomaliesTab anomalies={anomalies} refreshData={loadData} />
        )}
        {activeTab === 'ai' && <AiChatTab />}
      </main>
    </div>
  );
}
