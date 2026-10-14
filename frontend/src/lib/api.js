// The only place that talks to the backend. Relative /api by default (Vite
// proxies it in dev); VITE_API_URL for a deployed backend elsewhere.
import { storage } from './storage.js';

const BASE = import.meta.env.VITE_API_URL || '/api';
let token = storage.get('token');
let unauthorizedHandler = null;

export class ApiError extends Error {
  constructor(message, status, code = null) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

export function setToken(value) {
  token = value;
  if (value) storage.set('token', value);
  else storage.remove('token');
}

export const hasToken = () => Boolean(token);

// Called when a request made with a token comes back 401: the session is gone.
export function onUnauthorized(handler) {
  unauthorizedHandler = handler;
}

async function request(path, { method = 'GET', body, params } = {}) {
  const url = new URL(BASE + path, window.location.origin);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null && value !== '') url.searchParams.set(key, value);
    }
  }
  const headers = { Accept: 'application/json' };
  if (body) headers['Content-Type'] = 'application/json';
  const sentWithToken = Boolean(token);
  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(url, { method, headers, body: body ? JSON.stringify(body) : undefined });
  if (response.status === 204) return null;
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    if (response.status === 401 && sentWithToken) {
      setToken(null);
      unauthorizedHandler?.();
    }
    const detail = data?.detail;
    const message = typeof detail === 'string' ? detail : detail?.message || response.statusText || `HTTP ${response.status}`;
    throw new ApiError(message, response.status, typeof detail === 'object' ? detail?.code ?? null : null);
  }
  return data;
}

export const api = {
  health: () => request('/health'),

  market: {
    tickers: (symbols) => request('/market/tickers', { params: { symbols: symbols?.join(',') } }),
    ohlcv: (symbol, timeframe = '1h', limit = 60) => request('/market/ohlcv', { params: { symbol, timeframe, limit } }),
    indicators: (symbol, timeframe = '1h') => request('/market/indicators', { params: { symbol, timeframe } }),
    overview: () => request('/market/overview'),
    top: (limit = 20) => request('/market/top', { params: { limit } }),
  },

  futures: {
    overview: (symbol) => request('/futures/overview', { params: { symbol } }),
    top: (limit = 15) => request('/futures/top', { params: { limit } }),
    funding: (symbol, limit = 30) => request('/futures/funding', { params: { symbol, limit } }),
    openInterest: (symbol, period = '1h', limit = 168) => request('/futures/open-interest', { params: { symbol, period, limit } }),
    ratios: (symbol, period = '1h', limit = 48) => request('/futures/ratios', { params: { symbol, period, limit } }),
    ohlcv: (symbol, timeframe = '1h', limit = 200) => request('/futures/ohlcv', { params: { symbol, timeframe, limit } }),
    quarterly: () => request('/futures/quarterly'),
  },

  defi: {
    chains: (limit = 12) => request('/defi/chains', { params: { limit } }),
    protocols: (limit = 15) => request('/defi/protocols', { params: { limit } }),
    tvlHistory: (days = 180) => request('/defi/tvl-history', { params: { days } }),
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
    verify: (token) => request('/auth/verify', { method: 'POST', body: { token } }),
    resendVerification: (email) => request('/auth/resend-verification', { method: 'POST', body: { email } }),
    forgotPassword: (email) => request('/auth/forgot-password', { method: 'POST', body: { email } }),
    resetPassword: (token, password) => request('/auth/reset-password', { method: 'POST', body: { token, password } }),
  },

  admin: {
    users: (params) => request('/admin/users', { params }),
    updateUser: (id, body) => request(`/admin/users/${id}`, { method: 'PATCH', body }),
    deleteUser: (id) => request(`/admin/users/${id}`, { method: 'DELETE' }),
    stats: () => request('/admin/stats'),
  },
};
