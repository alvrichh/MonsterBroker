import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { api, hasToken, onUnauthorized, setToken } from '../lib/api.js';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(!hasToken());

  // A saved token: ask the API who it belongs to, drop it if it expired.
  useEffect(() => {
    onUnauthorized(() => setUser(null));
    if (!hasToken()) return;
    api.auth.me()
      .then(setUser)
      .catch(() => setToken(null))
      .finally(() => setReady(true));
  }, []);

  // Register and the one-shot links all answer with a TokenOut; a token means
  // the session starts now, no token means the email still has to be confirmed.
  const accept = useCallback((result) => {
    if (result.access_token) {
      setToken(result.access_token);
      setUser(result.user);
    }
    return result;
  }, []);

  const login = useCallback((body) => api.auth.login(body).then(accept), [accept]);
  const register = useCallback((body) => api.auth.register(body).then(accept), [accept]);
  const verify = useCallback((token) => api.auth.verify(token).then(accept), [accept]);
  const resetPassword = useCallback((token, password) => api.auth.resetPassword(token, password).then(accept), [accept]);
  const resendVerification = useCallback((email) => api.auth.resendVerification(email), []);
  const forgotPassword = useCallback((email) => api.auth.forgotPassword(email), []);
  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, ready, isAdmin: user?.role === 'admin', login, register, verify, resetPassword, resendVerification, forgotPassword, logout }),
    [user, ready, login, register, verify, resetPassword, resendVerification, forgotPassword, logout],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used inside <AuthProvider>');
  return context;
};
