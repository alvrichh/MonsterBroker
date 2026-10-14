import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { api, hasToken, onUnauthorized, setToken } from '../lib/api.js';
import { connectWallet, signMessage } from '../lib/wallet.js';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(!hasToken());
  const [providers, setProviders] = useState(null); // { providers: [...], wallet, chain_id }
  const providersRequest = useRef(null);
  // Bumped by any "sign in to see this" button; the header's bubble opens on it.
  const [signInRequest, setSignInRequest] = useState(0);
  const requestSignIn = useCallback(() => setSignInRequest((n) => n + 1), []);

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

  // Which one-click providers the backend has credentials for. Fetched once,
  // the first time a sign-in menu opens.
  const loadProviders = useCallback(() => {
    providersRequest.current ??= api.auth.providers()
      .then((result) => {
        setProviders(result);
        return result;
      })
      .catch(() => {
        providersRequest.current = null;
        return null;
      });
    return providersRequest.current;
  }, []);

  // OAuth lands on /auth/callback with a bare token: take it, then find out who it is.
  const acceptToken = useCallback((token) => {
    setToken(token);
    return api.auth.me()
      .then((me) => {
        setUser(me);
        return me;
      })
      .catch((error) => {
        setToken(null);
        throw error;
      });
  }, []);

  // Sign-In with Ethereum: the API writes a challenge, the wallet signs it.
  const challenge = useCallback(async () => {
    const address = await connectWallet();
    const { message } = await api.auth.walletNonce(address);
    const signature = await signMessage(address, message);
    return { message, signature };
  }, []);
  const loginWithWallet = useCallback(async () => {
    const { message, signature } = await challenge();
    return accept(await api.auth.walletVerify(message, signature));
  }, [accept, challenge]);
  const linkWallet = useCallback(async () => {
    const { message, signature } = await challenge();
    const me = await api.auth.walletLink(message, signature);
    setUser(me);
    return me;
  }, [challenge]);

  const value = useMemo(
    () => ({
      user, ready, isAdmin: user?.role === 'admin', providers, signInRequest,
      login, register, verify, resetPassword, resendVerification, forgotPassword, logout,
      loadProviders, acceptToken, loginWithWallet, linkWallet, requestSignIn,
    }),
    [user, ready, providers, signInRequest, login, register, verify, resetPassword, resendVerification,
      forgotPassword, logout, loadProviders, acceptToken, loginWithWallet, linkWallet, requestSignIn],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used inside <AuthProvider>');
  return context;
};
