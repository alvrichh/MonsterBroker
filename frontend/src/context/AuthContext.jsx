import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { api, hasToken, setToken } from '../lib/api.js';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(!hasToken());

  // A saved token: ask the API who it belongs to, drop it if it expired.
  useEffect(() => {
    if (!hasToken()) return;
    api.auth.me()
      .then(setUser)
      .catch(() => setToken(null))
      .finally(() => setReady(true));
  }, []);

  const accept = useCallback((result) => {
    setToken(result.access_token);
    setUser(result.user);
    return result.user;
  }, []);

  const login = useCallback((body) => api.auth.login(body).then(accept), [accept]);
  const register = useCallback((body) => api.auth.register(body).then(accept), [accept]);
  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
  }, []);

  const value = useMemo(() => ({ user, ready, login, register, logout }), [user, ready, login, register, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used inside <AuthProvider>');
  return context;
};
