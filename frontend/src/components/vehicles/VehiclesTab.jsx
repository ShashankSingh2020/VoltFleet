import React, { useState } from 'react';
import { Activity, Send } from 'lucide-react';
import { api } from '../../services/api';

export default function VehiclesTab({ vehicles, refreshData }) {
  const [selectedVehicle, setSelectedVehicle] = useState(vehicles[0] || null);
  const [soc, setSoc] = useState('45.0');
  const [temp, setTemp] = useState('32.0');
  const [power, setPower] = useState('-20.0');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [statusMessage, setStatusMessage] = useState(null);

  const handleSimulateTelemetry = async (e) => {
    e.preventDefault();
    if (!selectedVehicle) return;
    setIsSubmitting(true);
    setStatusMessage(null);

    const payload = [
      {
        vehicle_id: selectedVehicle.id,
        timestamp: new Date().toISOString(),
        soc_percent: soc,
        battery_temperature_celsius: temp,
        power_kw: power,
        cumulative_energy_kwh: '1520.5',
        speed_kmh: '45.0',
        odometer_km: '14265.0',
      },
    ];

    try {
      await api.postTelemetry(payload);
      setStatusMessage({ type: 'success', text: 'Telemetry packet ingested & vehicle state reconciled!' });
      if (refreshData) refreshData();
    } catch (err) {
      setStatusMessage({ type: 'error', text: err.message });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div className="lg:col-span-2 space-y-4">
        <h3 className="text-base font-semibold text-white">Active Fleet Inventory</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {vehicles.map((v) => (
            <div
              key={v.id}
              onClick={() => setSelectedVehicle(v)}
              className={`p-5 rounded-xl border cursor-pointer transition ${
                selectedVehicle?.id === v.id
                  ? 'bg-fleet-850 border-cyan-500/60 shadow-lg shadow-cyan-950/40'
                  : 'bg-fleet-900 border-fleet-800 hover:border-slate-700'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-bold text-white tracking-wide">{v.license_plate}</span>
                <span className={`px-2 py-0.5 rounded text-xs font-semibold ${
                  v.status === 'AVAILABLE' ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' :
                  v.status === 'IN_TRANSIT' ? 'bg-blue-950 text-blue-400 border border-blue-800' :
                  'bg-amber-950 text-amber-400 border border-amber-800'
                }`}>
                  {v.status}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-1">{v.nickname || 'Transit Delivery Van'} • VIN: {v.vin}</p>

              <div className="grid grid-cols-2 gap-2 mt-4 pt-3 border-t border-fleet-800 text-xs">
                <div>
                  <span className="text-slate-400">Current SoC:</span>
                  <p className="font-semibold text-white">{v.current_soc_percent}%</p>
                </div>
                <div>
                  <span className="text-slate-400">Odometer:</span>
                  <p className="font-semibold text-white">{v.odometer_km} km</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-fleet-900 border border-fleet-800 rounded-xl p-6">
        <div className="flex items-center gap-2 mb-4 text-cyan-400">
          <Activity className="w-5 h-5" />
          <h3 className="text-base font-semibold text-white">Telemetry Simulator</h3>
        </div>
        <p className="text-xs text-slate-400 mb-4">
          Inject live telemetry into the idempotent Celery/DB pipeline for <strong>{selectedVehicle?.license_plate || 'selected vehicle'}</strong>.
        </p>

        <form onSubmit={handleSimulateTelemetry} className="space-y-4">
          <div>
            <label className="text-xs text-slate-300 block mb-1">State of Charge (SoC %)</label>
            <input
              type="number"
              step="0.1"
              value={soc}
              onChange={(e) => setSoc(e.target.value)}
              className="w-full bg-fleet-850 border border-fleet-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-500"
            />
          </div>

          <div>
            <label className="text-xs text-slate-300 block mb-1">Battery Cell Temperature (°C)</label>
            <input
              type="number"
              step="0.1"
              value={temp}
              onChange={(e) => setTemp(e.target.value)}
              className="w-full bg-fleet-850 border border-fleet-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-500"
            />
            <span className="text-[11px] text-slate-400">Threshold: values &gt; 45°C trigger Critical Anomaly.</span>
          </div>

          <div>
            <label className="text-xs text-slate-300 block mb-1">Power Flow (kW)</label>
            <input
              type="number"
              step="0.1"
              value={power}
              onChange={(e) => setPower(e.target.value)}
              className="w-full bg-fleet-850 border border-fleet-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-500"
            />
            <span className="text-[11px] text-slate-400">Negative = Driving discharge, Positive = Charging.</span>
          </div>

          {statusMessage && (
            <div className={`p-3 rounded-lg text-xs ${
              statusMessage.type === 'success' ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' : 'bg-rose-950 text-rose-300 border border-rose-800'
            }`}>
              {statusMessage.text}
            </div>
          )}

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full py-2.5 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white rounded-lg text-xs font-semibold flex items-center justify-center gap-2 transition disabled:opacity-50"
          >
            <Send className="w-4 h-4" />
            {isSubmitting ? 'Ingesting Batch...' : 'Ingest Telemetry Batch'}
          </button>
        </form>
      </div>
    </div>
  );
}
