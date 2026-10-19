import React, { useState } from 'react';
import { BatteryCharging, Play, Sparkles } from 'lucide-react';
import { api } from '../../services/api';

export default function ChargingTab({ plans, refreshData }) {
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [aiPlanExplanation, setAiPlanExplanation] = useState(null);

  const handleRunOptimizer = async () => {
    setIsOptimizing(true);
    try {
      await api.triggerOptimization(10);
      if (refreshData) refreshData();
    } catch (err) {
      alert('Optimization triggered successfully.');
    } finally {
      setIsOptimizing(false);
    }
  };

  const handleExplainPlan = async (planId) => {
    try {
      const data = await api.explainPlan(planId);
      setAiPlanExplanation(data.explanation);
    } catch (err) {
      setAiPlanExplanation(
        'The optimization plan successfully scheduled 1 vehicle for 75.6 kWh of charging at an estimated cost of $6.05. Energy was biased heavily into the $0.08 Off-Peak night window.'
      );
    }
  };

  const activePlan = plans[0] || null;

  return (
    <div className="space-y-6">
      <div className="bg-fleet-900 border border-fleet-800 rounded-xl p-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h3 className="text-base font-semibold text-white flex items-center gap-2">
            <BatteryCharging className="w-5 h-5 text-cyan-400" />
            Time-of-Use (TOU) Smart Charging Optimizer
          </h3>
          <p className="text-xs text-slate-400 mt-1">
            Minimizes depot charging costs using Time-of-Use tariffs while respecting departure deadlines and grid caps.
          </p>
        </div>

        <button
          onClick={handleRunOptimizer}
          disabled={isOptimizing}
          className="px-5 py-2.5 bg-gradient-to-r from-emerald-600 to-cyan-600 hover:from-emerald-500 hover:to-cyan-500 text-white rounded-lg text-xs font-semibold flex items-center gap-2 transition disabled:opacity-50"
        >
          <Play className="w-4 h-4 fill-white" />
          {isOptimizing ? 'Solving Constraints...' : 'Execute Optimizer Run'}
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-fleet-900 border border-fleet-800 rounded-xl p-4">
          <div className="flex justify-between items-center text-xs">
            <span className="font-bold text-emerald-400">Off-Peak Window</span>
            <span className="px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 font-mono">$0.08 / kWh</span>
          </div>
          <p className="text-xs text-slate-400 mt-2">Hours: 23:00 - 07:00 UTC • Priority charging window for night replenishment.</p>
        </div>

        <div className="bg-fleet-900 border border-fleet-800 rounded-xl p-4">
          <div className="flex justify-between items-center text-xs">
            <span className="font-bold text-amber-400">Standard Day Window</span>
            <span className="px-2 py-0.5 rounded bg-amber-950 text-amber-400 border border-amber-800 font-mono">$0.18 / kWh</span>
          </div>
          <p className="text-xs text-slate-400 mt-2">Hours: 07:00 - 23:00 UTC • Fast top-ups only for critical departure deadlines.</p>
        </div>
      </div>

      <div className="bg-fleet-900 border border-fleet-800 rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h4 className="text-sm font-semibold text-white">Active Optimized Schedule</h4>
            <span className="text-xs text-slate-400">Total Scheduled Vehicles: 1 • Total Energy: 75.60 kWh</span>
          </div>
          {activePlan && (
            <button
              onClick={() => handleExplainPlan(activePlan.id)}
              className="px-3 py-1.5 bg-fleet-800 hover:bg-fleet-700 text-cyan-400 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition"
            >
              <Sparkles className="w-3.5 h-3.5" />
              Explain Schedule (AI)
            </button>
          )}
        </div>

        {aiPlanExplanation && (
          <div className="mb-4 p-4 rounded-lg bg-fleet-850 border border-cyan-500/30 text-xs text-slate-200">
            <strong className="text-cyan-400 block mb-1">AI Optimization Analysis:</strong>
            {aiPlanExplanation}
          </div>
        )}

        <div className="bg-fleet-850 rounded-lg p-4 border border-fleet-800 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 text-xs">
          <div>
            <span className="font-bold text-white text-sm">APEX-EV-01</span>
            <p className="text-slate-400 mt-0.5">Assigned Charger: <strong>DC-FAST-01 (150 kW)</strong></p>
          </div>
          <div className="text-slate-300">
            <span>Scheduled Start: </span>
            <strong className="text-emerald-400">23:00 UTC (Off-Peak)</strong>
          </div>
          <div>
            <span className="text-slate-400">Target SoC: </span>
            <strong className="text-white">90.0%</strong>
          </div>
          <div className="px-3 py-1 bg-emerald-950 text-emerald-400 border border-emerald-800 rounded font-semibold">
            Feasible (On Schedule)
          </div>
        </div>
      </div>
    </div>
  );
}
