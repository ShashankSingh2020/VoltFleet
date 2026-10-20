const BASE_URL = 'http://127.0.0.1:8000/api/v1';

class ApiClient {
  constructor() {
    this.token = localStorage.getItem('voltfleet_token') || null;
  }

  setToken(token) {
    this.token = token;
    if (token) {
      localStorage.setItem('voltfleet_token', token);
    } else {
      localStorage.removeItem('voltfleet_token');
    }
  }

  async login(email, password) {
    if (!email || !password) {
      if (this.token) return { access: this.token };
      return null;
    }

    try {
      const response = await fetch(`${BASE_URL}/auth/token/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        throw new Error('Authentication failed');
      }

      const data = await response.json();
      this.setToken(data.access);
      return data;
    } catch (err) {
      console.error('Login error:', err);
      throw err;
    }
  }

  logout() {
    this.setToken(null);
  }

  async fetchWithAuth(endpoint, options = {}) {
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const res = await fetch(`${BASE_URL}${endpoint}`, {
      ...options,
      headers,
    });

    if (res.status === 401) {
      this.logout();
      window.dispatchEvent(new Event('voltfleet_auth_expired'));
      throw new Error('Session expired');
    }

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || errData.error || `HTTP error ${res.status}`);
    }

    return res.json();
  }

  // Core Fleet & Analytics
  getFleetSummary() {
    return this.fetchWithAuth('/analytics/summary/');
  }

  getVehicles() {
    return this.fetchWithAuth('/vehicles/');
  }

  getAnomalies() {
    return this.fetchWithAuth('/anomalies/');
  }

  getChargingPlans() {
    return this.fetchWithAuth('/optimizer/plans/');
  }

  // Telemetry Ingestion
  postTelemetry(payload) {
    return this.fetchWithAuth('/telemetry/ingest/', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  ingestTelemetry(events) {
    return this.fetchWithAuth('/telemetry/ingest/batch/', {
      method: 'POST',
      body: JSON.stringify({ events }),
    });
  }

  // Anomaly Actions
  acknowledgeAnomaly(id, notes = '') {
    return this.fetchWithAuth(`/anomalies/${id}/acknowledge/`, {
      method: 'POST',
      body: JSON.stringify({ notes }),
    });
  }

  resolveAnomaly(id, notes = '') {
    return this.fetchWithAuth(`/anomalies/${id}/resolve/`, {
      method: 'POST',
      body: JSON.stringify({ notes }),
    });
  }

  // Optimizer (using correct /generate/ route)
  triggerOptimization(horizonHours = 8) {
    return this.fetchWithAuth('/optimizer/plans/generate/', {
      method: 'POST',
      body: JSON.stringify({ horizon_hours: horizonHours }),
    });
  }

  // AI Assistant Copilot & Diagnostics
  askAIChat(query) {
    return this.fetchWithAuth('/ai/chat/', {
      method: 'POST',
      body: JSON.stringify({ query }),
    });
  }

  sendAiChat(query) {
    return this.askAIChat(query);
  }

  explainAnomaly(id) {
    return this.fetchWithAuth(`/ai/anomalies/${id}/explain/`);
  }

  explainPlan(planId) {
    return this.fetchWithAuth(`/ai/plans/${planId}/explain/`);
  }
}

export const api = new ApiClient();
