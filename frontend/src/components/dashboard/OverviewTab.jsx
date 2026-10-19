import React from 'react';
import { Truck, BatteryCharging, AlertTriangle, Gauge, TrendingUp, Zap } from 'lucide-react';

export default function OverviewTab({ summary, anomalies, vehicles, setActiveTab }) {
  const criticalCount = anomalies.filter(a => a.severity === 'CRITICAL' && a.status === 'OPEN').length;

  return (
    <div className="space-y-6">
      {criticalCount > 0 && (
        <div className="bg-rose-950/40 border border-rose-500/40 rounded-xl p-4 flex items-center justify-between shadow-lg shadow-rose-950/30">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-rose-500/20 border border-rose-500/40 flex items-center justify-center text-rose-400">
              <AlertTriangle className="w-5 h-5 animate-bounce" />
            </div>
            <div>
              <h4 className="text-sm font-semibold text-rose-300">
                {criticalCount} Critical Telemetry Anomaly Detected
              </h4>
              <p className="text-xs text-rose-400/80">
                Active thermal spike on APEX-EV-01 (52.5°C). Immediate coolant inspection or power throttling recommended.
              </p>
            </div>
          </div>
          <button
            onClick={() => setActiveTab('anomalies')}
            className="px-4 py-2 bg-rose-600 hover:bg-rose-500 text-white rounded-lg text-xs font-semibold transition"
          >
            Review Anomaly
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-fleet-900 border border-fleet-800 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs uppercase font-medium tracking-wider">Active Vehicles</span>
            <Truck className="w-5 h-5 text-cyan-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-white">{summary?.total_vehicles || 2}</span>
            <span className="text-xs text-emerald-400">100% Operational</span>
          </div>
          <div className="mt-3 flex gap-2 text-xs text-slate-400">
            <span className="bg-fleet-800 px-2 py-0.5 rounded">1 In Transit</span>
            <span className="bg-fleet-800 px-2 py-0.5 rounded">1 Available</span>
          </div>
        </div>

        <div className="bg-fleet-900 border border-fleet-800 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs uppercase font-medium tracking-wider">Fleet Avg State of Charge</span>
            <BatteryCharging className="w-5 h-5 text-emerald-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-white">{summary?.average_soc_percent || '45.1'}%</span>
            <span className="text-xs text-slate-400">Depot Target: 85%</span>
          </div>
          <div className="w-full bg-fleet-800 rounded-full h-2 mt-3 overflow-hidden">
            <div
              className="bg-gradient-to-r from-emerald-500 to-cyan-400 h-2 rounded-full"
              style={{ width: `${parseFloat(summary?.average_soc_percent || 45.1)}%` }}
            />
          </div>
        </div>

        <div className="bg-fleet-900 border border-fleet-800 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs uppercase font-medium tracking-wider">Total Energy Consumed</span>
            <Zap className="w-5 h-5 text-amber-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-white">{summary?.total_energy_kwh || '38.5'}</span>
            <span className="text-xs text-slate-400">kWh</span>
          </div>
          <p className="mt-3 text-xs text-slate-400">Distance logged: {summary?.total_distance_km || '46.2'} km</p>
        </div>

        <div className="bg-fleet-900 border border-fleet-800 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs uppercase font-medium tracking-wider">Fleet Efficiency</span>
            <Gauge className="w-5 h-5 text-indigo-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-white">{summary?.average_efficiency_kwh_per_100km || '21.5'}</span>
            <span className="text-xs text-slate-400">kWh / 100km</span>
          </div>
          <div className="mt-3 flex items-center gap-1 text-xs text-emerald-400">
            <TrendingUp className="w-3.5 h-3.5" />
            <span>Optimal range efficiency</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="bg-fleet-900 border border-fleet-800 rounded-xl p-6 lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-base font-semibold text-white">North Depot Supercharger Hub</h3>
              <p className="text-xs text-slate-400">400 Terminal Way • Grid Interconnect Capacity: 400.0 kW</p>
            </div>
            <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-950 text-emerald-400 border border-emerald-800">
              Grid Stabilized
            </span>
          </div>

          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-xs text-slate-400 mb-1">
                <span>Active Demand: 125.0 kW</span>
                <span>Peak Limit: 400.0 kW (31.2% Utilized)</span>
              </div>
              <div className="w-full bg-fleet-800 rounded-full h-3 overflow-hidden">
                <div className="bg-cyan-500 h-3 rounded-full" style={{ width: '31.2%' }} />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 pt-2">
              <div className="bg-fleet-850 p-3 rounded-lg border border-fleet-800">
                <span className="text-xs text-slate-400">Bay 1 (DC-FAST-01)</span>
                <p className="text-sm font-semibold text-white mt-1">150 kW Max • 94% Eff</p>
                <span className="text-xs text-cyan-400">Allocated to APEX-EV-01</span>
              </div>
              <div className="bg-fleet-850 p-3 rounded-lg border border-fleet-800">
                <span className="text-xs text-slate-400">Bay 2 (DC-FAST-02)</span>
                <p className="text-sm font-semibold text-white mt-1">100 kW Max • 92% Eff</p>
                <span className="text-xs text-emerald-400">Standby (Available)</span>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-fleet-900 border border-fleet-800 rounded-xl p-6 flex flex-col justify-between">
          <div>
            <h3 className="text-base font-semibold text-white">Smart Optimization</h3>
            <p className="text-xs text-slate-400 mt-1">
              Time-of-Use tariffs minimize off-peak energy cost (\$0.08/kWh after 23:00 vs \$0.18/kWh daytime).
            </p>
            <div className="mt-4 p-3 rounded-lg bg-fleet-850 border border-fleet-800 text-xs space-y-1">
              <div className="flex justify-between text-slate-300">
                <span>Next Off-Peak Window:</span>
                <span className="font-semibold text-emerald-400">23:00 - 07:00 UTC</span>
              </div>
              <div className="flex justify-between text-slate-300">
                <span>Est. Cost Reduction:</span>
                <span className="font-semibold text-cyan-400">55.6% vs Flat Rate</span>
              </div>
            </div>
          </div>
          <button
            onClick={() => setActiveTab('charging')}
            className="w-full mt-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg text-xs font-semibold transition"
          >
            Open Optimizer Console
          </button>
        </div>
      </div>
    </div>
  );
}
