import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import OverviewTab from './components/dashboard/OverviewTab';
import VehiclesTab from './components/vehicles/VehiclesTab';
import ChargingTab from './components/charging/ChargingTab';
import AnomaliesTab from './components/anomalies/AnomaliesTab';
import AiChatTab from './components/ai/AiChatTab';
import FleetMap from './components/map/FleetMap';
import { api } from './services/api';
import { AlertCircle, Lock, LogIn } from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [isAuthenticated, setIsAuthenticated] = useState(!!api.token);
  const [isOnline, setIsOnline] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [loginError, setLoginError] = useState('');
  const [isLoggingIn, setIsLoggingIn] = useState(false);

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
    if (!api.token) return;
    try {
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
      console.warn('Backend offline, using fallback state:', err);
      setIsOnline(false);
    }
  };

  const handleLogin = async (e) => {
    e?.preventDefault();
    setLoginError('');
    setIsLoggingIn(true);
    try {
      await api.login(loginEmail, loginPassword);
      setIsAuthenticated(true);
      loadData();
    } catch (err) {
      setLoginError(err.message || 'Invalid credentials');
    } finally {
      setIsLoggingIn(false);
    }
  };

  const fillDemoCredentials = () => {
    setLoginEmail('admin@voltfleet.io');
    setLoginPassword('Password123!');
  };

  useEffect(() => {
    if (isAuthenticated) {
      loadData();
    }

    const handleExpired = () => {
      setIsAuthenticated(false);
    };
    window.addEventListener('voltfleet_auth_expired', handleExpired);
    return () => window.removeEventListener('voltfleet_auth_expired', handleExpired);
  }, [isAuthenticated]);

  useEffect(() => {
    const token = api.token;
    if (!token) {
      setWsConnected(false);
      return;
    }

    // Pass the JWT token in query string for consumer handshake
    const wsUrl = `ws://127.0.0.1:8000/ws/telemetry/?token=${encodeURIComponent(token)}`;
    const socket = new WebSocket(wsUrl);

    socket.onopen = () => {
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

        if (livePoint.latitude && livePoint.longitude) {
          setTelemetryHistory((prev) => [...prev.slice(-30), livePoint]);
        }
      } catch (e) {
        console.error('Error parsing live telemetry frame:', e);
      }
    };

    socket.onclose = () => setWsConnected(false);
    socket.onerror = () => setWsConnected(false);

    return () => socket.close();
  }, [isAuthenticated, api.token]);

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-fleet-950 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-fleet-900 border border-fleet-800 rounded-xl p-8 shadow-2xl space-y-6">
          <div className="text-center space-y-2">
            <div className="inline-flex p-3 bg-emerald-500/10 text-emerald-400 rounded-lg">
              <Lock className="w-8 h-8" />
            </div>
            <h2 className="text-2xl font-bold text-slate-100">VoltFleet Operator Login</h2>
            <p className="text-sm text-slate-400">Enter your credentials to access the fleet console</p>
          </div>

          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Email Address</label>
              <input
                type="email"
                required
                value={loginEmail}
                onChange={(e) => setLoginEmail(e.target.value)}
                placeholder="operator@voltfleet.io"
                className="w-full bg-fleet-950 border border-fleet-700 rounded-lg px-4 py-2.5 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-emerald-500 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Password</label>
              <input
                type="password"
                required
                value={loginPassword}
                onChange={(e) => setLoginPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full bg-fleet-950 border border-fleet-700 rounded-lg px-4 py-2.5 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-emerald-500 text-sm"
              />
            </div>

            {loginError && (
              <div className="p-3 bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs rounded-lg">
                {loginError}
              </div>
            )}

            <button
              type="submit"
              disabled={isLoggingIn}
              className="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-medium py-2.5 rounded-lg transition-colors flex items-center justify-center gap-2 text-sm"
            >
              <LogIn className="w-4 h-4" />
              {isLoggingIn ? 'Authenticating...' : 'Sign In'}
            </button>
          </form>

          <div className="pt-2 border-t border-fleet-800 text-center">
            <button
              type="button"
              onClick={fillDemoCredentials}
              className="text-xs text-emerald-400 hover:text-emerald-300 font-mono"
            >
              Fill Demo Credentials (admin@voltfleet.io)
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-fleet-950 text-slate-100 flex flex-col">
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        anomalyCount={anomalies.filter((a) => a.status === 'OPEN').length}
        isOnline={isOnline}
      />

      {!isOnline && (
        <div className="bg-amber-950/80 border-b border-amber-600/50 px-4 py-2 text-xs flex items-center justify-center gap-2 text-amber-200">
          <AlertCircle className="w-4 h-4 text-amber-400" />
          <span><strong>Notice:</strong> Backend API offline or unreachable. Displaying local simulated demo dataset.</span>
        </div>
      )}

      <div className="bg-fleet-900 border-b border-fleet-800 px-4 py-1 text-xs flex justify-between items-center text-slate-400">
        <span className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`} />
          {wsConnected ? 'WebSocket Stream: Connected (Scoped to Tenant)' : 'WebSocket Stream: Disconnected'}
        </span>
        <button
          onClick={() => {
            api.logout();
            setIsAuthenticated(false);
          }}
          className="hover:text-rose-400 transition-colors"
        >
          Sign Out
        </button>
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
