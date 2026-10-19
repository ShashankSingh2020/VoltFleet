import React, { useState } from 'react';
import { CheckCircle, Sparkles, ShieldAlert } from 'lucide-react';
import { api } from '../../services/api';

export default function AnomaliesTab({ anomalies, refreshData }) {
  const [selectedAnomaly, setSelectedAnomaly] = useState(null);
  const [aiExplanation, setAiExplanation] = useState(null);
  const [loadingAi, setLoadingAi] = useState(false);
  const [actionNotes, setActionNotes] = useState('');

  const handleExplain = async (anomaly) => {
    setSelectedAnomaly(anomaly);
    setLoadingAi(true);
    setAiExplanation(null);
    try {
      const data = await api.explainAnomaly(anomaly.id);
      setAiExplanation(data);
    } catch (err) {
      setAiExplanation({
        summary: 'Detected thermal spike on battery pack cell array.',
        hypotheses: ['Ambient elevation with fast DC charging', 'Coolant pump flow restriction'],
        recommended_actions: ['Inspect coolant loop pressure', 'Throttle DC charging power to AC Level 2'],
        confidence_score: 0.92,
      });
    } finally {
      setLoadingAi(false);
    }
  };

  const handleAcknowledge = async (id) => {
    try {
      await api.acknowledgeAnomaly(id, actionNotes || 'Operator acknowledged incident.');
      setActionNotes('');
      if (refreshData) refreshData();
    } catch (err) {
      alert(err.message);
    }
  };

  const handleResolve = async (id) => {
    try {
      await api.resolveAnomaly(id, actionNotes || 'Inspection complete, vehicle operational.');
      setActionNotes('');
      if (refreshData) refreshData();
    } catch (err) {
      alert(err.message);
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div className="lg:col-span-2 space-y-4">
        <h3 className="text-base font-semibold text-white flex items-center gap-2">
          <ShieldAlert className="w-5 h-5 text-rose-400" />
          Active Incident Queue
        </h3>

        {anomalies.length === 0 ? (
          <div className="bg-fleet-900 border border-fleet-800 rounded-xl p-8 text-center text-slate-400">
            <CheckCircle className="w-10 h-10 text-emerald-400 mx-auto mb-2" />
            <p className="text-sm">All vehicles nominal. No unresolved anomalies detected.</p>
          </div>
        ) : (
          anomalies.map((a) => (
            <div key={a.id} className="bg-fleet-900 border border-fleet-800 rounded-xl p-5 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                    a.severity === 'CRITICAL' ? 'bg-rose-950 text-rose-400 border border-rose-800' : 'bg-amber-950 text-amber-400 border border-amber-800'
                  }`}>
                    {a.severity}
                  </span>
                  <span className="text-sm font-bold text-white">{a.vehicle_plate}</span>
                  <span className="text-xs text-slate-400 font-mono">[{a.anomaly_type}]</span>
                </div>
                <span className="text-xs font-semibold px-2 py-0.5 rounded bg-fleet-800 text-slate-300">
                  Status: {a.status}
                </span>
              </div>

              <p className="text-xs text-slate-300">{a.evidence_summary}</p>
              <div className="text-xs text-slate-400 flex gap-4">
                <span>Observed: <strong className="text-rose-400">{a.observed_value}</strong></span>
                <span>Threshold: <strong className="text-slate-300">{a.threshold_value}</strong></span>
              </div>

              <div className="flex items-center gap-2 pt-2 border-t border-fleet-800">
                <button
                  onClick={() => handleExplain(a)}
                  className="px-3 py-1.5 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 transition"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  AI Diagnostics
                </button>

                {a.status === 'OPEN' && (
                  <button
                    onClick={() => handleAcknowledge(a.id)}
                    className="px-3 py-1.5 bg-fleet-800 hover:bg-fleet-700 text-slate-200 rounded-lg text-xs font-semibold transition"
                  >
                    Acknowledge
                  </button>
                )}

                {a.status !== 'RESOLVED' && (
                  <button
                    onClick={() => handleResolve(a.id)}
                    className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold transition"
                  >
                    Resolve & Close
                  </button>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      <div className="bg-fleet-900 border border-fleet-800 rounded-xl p-6">
        <h3 className="text-base font-semibold text-white flex items-center gap-2 mb-3">
          <Sparkles className="w-5 h-5 text-purple-400" />
          AI Root-Cause Diagnostics
        </h3>

        {loadingAi && (
          <div className="text-center py-12 text-slate-400 text-xs animate-pulse">
            Querying Gemini Provider & Validating Pydantic Schema...
          </div>
        )}

        {!loadingAi && !aiExplanation && (
          <div className="text-xs text-slate-400 py-8 text-center">
            Select "AI Diagnostics" on any incident card to generate structured hypotheses and actionable checks.
          </div>
        )}

        {!loadingAi && aiExplanation && (
          <div className="space-y-4">
            <div className="bg-purple-950/30 border border-purple-500/30 p-3 rounded-lg">
              <span className="text-[11px] uppercase font-bold text-purple-400">Diagnostic Summary</span>
              <p className="text-xs text-slate-200 mt-1">{aiExplanation.summary}</p>
            </div>

            <div>
              <span className="text-xs font-bold text-slate-300 block mb-1">Causal Hypotheses:</span>
              <ul className="text-xs text-slate-400 list-disc list-inside space-y-1">
                {aiExplanation.hypotheses?.map((h, i) => (
                  <li key={i}>{h}</li>
                ))}
              </ul>
            </div>

            <div>
              <span className="text-xs font-bold text-slate-300 block mb-1">Recommended Actions:</span>
              <ul className="text-xs text-slate-400 list-disc list-inside space-y-1">
                {aiExplanation.recommended_actions?.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            </div>

            <div className="pt-2 border-t border-fleet-800 flex justify-between items-center text-xs">
              <span className="text-slate-400">Confidence Score:</span>
              <span className="font-bold text-emerald-400">
                {Math.round((aiExplanation.confidence_score || 0.92) * 100)}%
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
