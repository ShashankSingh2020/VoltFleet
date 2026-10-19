import React from 'react';
import { Zap, ShieldCheck, Radio } from 'lucide-react';

export default function Header({ activeTab, setActiveTab, anomalyCount, isOnline }) {
  const tabs = [
    { id: 'dashboard', label: 'Fleet Overview & GPS' },
    { id: 'vehicles', label: 'Telematics & Simulator' },
    { id: 'charging', label: 'Smart Charging' },
    { id: 'anomalies', label: 'Health & Anomalies', badge: anomalyCount },
    { id: 'ai', label: 'AI Fleet Copilot' },
  ];

  return (
    <header className="bg-fleet-900 border-b border-fleet-800 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
              <Zap className="w-5 h-5 text-white" />
            </div>
            <div>
              <span className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
                VoltFleet <span className="text-xs px-2 py-0.5 rounded-full bg-cyan-950 text-cyan-400 border border-cyan-800">Intelligence</span>
              </span>
              <p className="text-xs text-slate-400">Apex Fleet Logistics (North Depot Hub)</p>
            </div>
          </div>

          <nav className="hidden md:flex space-x-1">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-3 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 ${
                  activeTab === tab.id
                    ? 'bg-fleet-800 text-cyan-400 border border-cyan-500/30 shadow-inner'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-fleet-850'
                }`}
              >
                {tab.label}
                {tab.badge > 0 && (
                  <span className="px-1.5 py-0.5 rounded-full text-xs font-bold bg-rose-500/20 text-rose-400 border border-rose-500/30">
                    {tab.badge}
                  </span>
                )}
              </button>
            ))}
          </nav>

          <div className="flex items-center gap-3">
            <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full bg-fleet-850 border border-fleet-800 text-xs">
              <Radio className={`w-3.5 h-3.5 ${isOnline ? 'text-emerald-400 animate-pulse' : 'text-amber-400'}`} />
              <span className="text-slate-300 font-mono">
                {isOnline ? 'ASGI 8000 LIVE' : 'DEMO MODE'}
              </span>
            </div>

            <div className="flex items-center gap-2 text-xs text-slate-400 bg-fleet-850 px-3 py-1.5 rounded-lg border border-fleet-800">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span>admin@voltfleet.io</span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
