// The only place that talks to the backend. Relative /api by default (Vite
// proxies it in dev); VITE_API_URL for a deployed backend elsewhere.
import { storage } from './storage.js';

const BASE = import.meta.env.VITE_API_URL || '/api';
let token = storage.get('token');

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

export function setToken(value) {
  token = value;
  if (value) storage.set('token', value);
  else storage.remove('token');
}

export const hasToken = () => Boolean(token);

async function request(path, { method = 'GET', body, params } = {}) {
  const url = new URL(BASE + path, window.location.origin);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null && value !== '') url.searchParams.set(key, value);
    }
  }
  const headers = { Accept: 'application/json' };
  if (body) headers['Content-Type'] = 'application/json';
  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(url, { method, headers, body: body ? JSON.stringify(body) : undefined });
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = typeof data?.detail === 'string' ? data.detail : response.statusText;
    throw new ApiError(detail || `HTTP ${response.status}`, response.status);
  }
  return data;
}

export const api = {
  health: () => request('/health'),

  market: {
    tickers: (symbols) => request('/market/tickers', { params: { symbols: symbols?.join(',') } }),
    ohlcv: (symbol, timeframe = '1h', limit = 60) => request('/market/ohlcv', { params: { symbol, timeframe, limit } }),
    indicators: (symbol, timeframe = '1h') => request('/market/indicators', { params: { symbol, timeframe } }),
  },

  bot: {
    status: () => request('/bot/status'),
    strategies: () => request('/bot/strategies'),
    tick: () => request('/bot/tick', { method: 'POST' }),
    reset: () => request('/bot/reset', { method: 'POST' }),
    config: (body) => request('/bot/config', { method: 'PUT', body }),
    trades: (limit = 50) => request('/bot/trades', { params: { limit } }),
  },

  news: {
    latest: () => request('/news/latest'),
    archive: (params) => request('/news/archive', { params }),
    tags: () => request('/news/tags'),
    refresh: () => request('/news/refresh', { method: 'POST' }),
  },

  wallet: {
    chains: () => request('/wallet/chains'),
    balance: (address, chain) => request('/wallet/balance', { params: { address, chain } }),
  },

  auth: {
    register: (body) => request('/auth/register', { method: 'POST', body }),
    login: (body) => request('/auth/login', { method: 'POST', body }),
    me: () => request('/auth/me'),
  },
};
