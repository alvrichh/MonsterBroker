import { Route, Routes } from 'react-router-dom';
import Footer from './components/Footer.jsx';
import Header from './components/Header.jsx';
import RequireAuth from './components/RequireAuth.jsx';
import { AuthProvider } from './context/AuthContext.jsx';
import { I18nProvider } from './i18n/I18nContext.jsx';
import Admin from './pages/Admin.jsx';
import Bot from './pages/Bot.jsx';
import Dashboard from './pages/Dashboard.jsx';
import Defi from './pages/Defi.jsx';
import ForgotPassword from './pages/ForgotPassword.jsx';
import Futures from './pages/Futures.jsx';
import Home from './pages/Home.jsx';
import Login from './pages/Login.jsx';
import News from './pages/News.jsx';
import NotFound from './pages/NotFound.jsx';
import Register from './pages/Register.jsx';
import ResetPassword from './pages/ResetPassword.jsx';
import Verify from './pages/Verify.jsx';
import Wallet from './pages/Wallet.jsx';

// The home page and the account pages are public; the app itself needs a
// confirmed account. /admin needs the admin role on top.
const protect = (page, admin = false) => <RequireAuth admin={admin}>{page}</RequireAuth>;

export default function App() {
  return (
    <I18nProvider>
      <AuthProvider>
        <Header />
        <main className="page">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/verify" element={<Verify />} />
            <Route path="/forgot" element={<ForgotPassword />} />
            <Route path="/reset" element={<ResetPassword />} />
            <Route path="/dashboard" element={protect(<Dashboard />)} />
            <Route path="/futures" element={protect(<Futures />)} />
            <Route path="/bot" element={protect(<Bot />)} />
            <Route path="/news" element={protect(<News />)} />
            <Route path="/wallet" element={protect(<Wallet />)} />
            <Route path="/defi" element={protect(<Defi />)} />
            <Route path="/admin" element={protect(<Admin />, true)} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </main>
        <Footer />
      </AuthProvider>
    </I18nProvider>
  );
}
