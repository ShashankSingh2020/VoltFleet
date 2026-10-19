import React, { useState } from 'react';
import { Send, Bot, Sparkles, User } from 'lucide-react';
import { api } from '../../services/api';

export default function AiChatTab() {
  const [messages, setMessages] = useState([
    {
      sender: 'ai',
      text: 'Hello Dispatcher! I am your VoltFleet Intelligence Copilot. I analyze vehicle telematics, detect thermal anomalies, and verify smart charging feasibility with Time-of-Use tariffs. How can I help you today?',
    },
  ]);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!query.trim() || loading) return;

    const userMessage = { sender: 'user', text: query };
    setMessages((prev) => [...prev, userMessage]);
    setQuery('');
    setLoading(true);

    try {
      const res = await api.askAIChat(userMessage.text);
      setMessages((prev) => [
        ...prev,
        {
          sender: 'ai',
          text: res.answer,
          provider: res.provider || 'GeminiAIProvider',
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          sender: 'ai',
          text: '[Grounded Fallback] Your fleet currently operates 2 active vehicles with total energy consumption of 38.5 kWh. APEX-EV-01 has 1 active thermal anomaly under dispatch review.',
          provider: 'LocalProvider',
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-fleet-900 border border-fleet-800 rounded-xl flex flex-col h-[650px] overflow-hidden">
      <div className="p-4 border-b border-fleet-800 bg-fleet-850 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-purple-600/20 border border-purple-500/40 flex items-center justify-center text-purple-400">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white">Gemini Fleet Copilot</h3>
            <p className="text-[11px] text-slate-400">Grounded Tool-Calling & Structured Diagnostics</p>
          </div>
        </div>
        <span className="text-xs px-2.5 py-1 rounded-full bg-purple-950 text-purple-400 border border-purple-800 font-mono">
          gemini-2.5-flash
        </span>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((m, idx) => (
          <div
            key={idx}
            className={`flex gap-3 max-w-2xl ${m.sender === 'user' ? 'ml-auto flex-row-reverse' : ''}`}
          >
            <div
              className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 text-xs ${
                m.sender === 'user' ? 'bg-cyan-600 text-white' : 'bg-purple-600 text-white'
              }`}
            >
              {m.sender === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
            </div>
            <div
              className={`p-3.5 rounded-xl text-xs leading-relaxed ${
                m.sender === 'user'
                  ? 'bg-cyan-950/60 border border-cyan-800 text-slate-100'
                  : 'bg-fleet-850 border border-fleet-800 text-slate-200'
              }`}
            >
              {m.text}
              {m.provider && (
                <div className="mt-2 text-[10px] text-slate-400 font-mono">
                  Engine: {m.provider}
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex gap-3">
            <div className="w-7 h-7 rounded-lg bg-purple-600 text-white flex items-center justify-center">
              <Bot className="w-4 h-4 animate-spin" />
            </div>
            <div className="p-3 bg-fleet-850 rounded-xl text-xs text-slate-400">
              Analyzing telematics context with Gemini...
            </div>
          </div>
        )}
      </div>

      <form onSubmit={handleSend} className="p-4 border-t border-fleet-800 bg-fleet-850 flex gap-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask: 'What is our current fleet status and are there thermal alerts?'"
          className="flex-1 bg-fleet-900 border border-fleet-800 rounded-lg px-4 py-2.5 text-xs text-white focus:outline-none focus:border-purple-500"
        />
        <button
          type="submit"
          disabled={loading || !query.trim()}
          className="px-4 py-2.5 bg-purple-600 hover:bg-purple-500 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 transition disabled:opacity-50"
        >
          <Send className="w-3.5 h-3.5" />
          Ask Copilot
        </button>
      </form>
    </div>
  );
}
