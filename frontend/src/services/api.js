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
      // Re-use stored token if already authenticated
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

  ingestTelemetry(events) {
    return this.fetchWithAuth('/telemetry/ingest/batch/', {
      method: 'POST',
      body: JSON.stringify({ events }),
    });
  }

  sendAiChat(query) {
    return this.fetchWithAuth('/ai/chat/', {
      method: 'POST',
      body: JSON.stringify({ query }),
    });
  }
}

export const api = new ApiClient();
