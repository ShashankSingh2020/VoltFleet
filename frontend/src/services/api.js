const API_BASE = 'http://127.0.0.1:8000/api/v1';

class ApiService {
  constructor() {
    this.token = localStorage.getItem('voltfleet_token') || null;
  }

  setToken(token) {
    this.token = token;
    if (token) localStorage.setItem('voltfleet_token', token);
    else localStorage.removeItem('voltfleet_token');
  }

  async login(email = 'admin@voltfleet.io', password = 'Admin@123456') {
    try {
      const res = await fetch(`${API_BASE}/auth/token/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) throw new Error('Authentication failed');
      const data = await res.json();
      this.setToken(data.access);
      return data;
    } catch (err) {
      console.warn('Backend login fallback to mock:', err.message);
      return null;
    }
  }

  async fetchWithAuth(url, options = {}) {
    const headers = {
      'Content-Type': 'application/json',
      ...(this.token ? { Authorization: `Bearer ${this.token}` } : {}),
      ...(options.headers || {}),
    };
    const res = await fetch(`${API_BASE}${url}`, { ...options, headers });
    if (!res.ok) {
      const errorBody = await res.text();
      throw new Error(`API Error [${res.status}]: ${errorBody}`);
    }
    return res.json();
  }

  getFleetSummary() {
    return this.fetchWithAuth('/analytics/summary/');
  }

  getVehicles() {
    return this.fetchWithAuth('/vehicles/');
  }

  postTelemetry(payload) {
    return this.fetchWithAuth('/telemetry/ingest/', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  getAnomalies() {
    return this.fetchWithAuth('/anomalies/');
  }

  acknowledgeAnomaly(id, notes) {
    return this.fetchWithAuth(`/anomalies/${id}/acknowledge/`, {
      method: 'POST',
      body: JSON.stringify({ notes }),
    });
  }

  resolveAnomaly(id, notes) {
    return this.fetchWithAuth(`/anomalies/${id}/resolve/`, {
      method: 'POST',
      body: JSON.stringify({ notes }),
    });
  }

  getChargingPlans() {
    return this.fetchWithAuth('/optimizer/plans/');
  }

  triggerOptimization(horizonHours = 8) {
    return this.fetchWithAuth('/optimizer/plans/optimize/', {
      method: 'POST',
      body: JSON.stringify({ horizon_hours: horizonHours }),
    });
  }

  askAIChat(query) {
    return this.fetchWithAuth('/ai/chat/', {
      method: 'POST',
      body: JSON.stringify({ query }),
    });
  }

  explainAnomaly(id) {
    return this.fetchWithAuth(`/ai/anomalies/${id}/explain/`);
  }

  explainPlan(planId) {
    return this.fetchWithAuth(`/ai/plans/${planId}/explain/`);
  }
}

export const api = new ApiService();
