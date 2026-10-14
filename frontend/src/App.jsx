import { Route, Routes } from 'react-router-dom';
import Header from './components/Header.jsx';
import Footer from './components/Footer.jsx';
import { AuthProvider } from './context/AuthContext.jsx';
import { I18nProvider } from './i18n/I18nContext.jsx';
import Bot from './pages/Bot.jsx';
import Dashboard from './pages/Dashboard.jsx';
import Defi from './pages/Defi.jsx';
import Futures from './pages/Futures.jsx';
import Home from './pages/Home.jsx';
import Login from './pages/Login.jsx';
import News from './pages/News.jsx';
import NotFound from './pages/NotFound.jsx';
import Register from './pages/Register.jsx';
import Wallet from './pages/Wallet.jsx';

export default function App() {
  return (
    <I18nProvider>
      <AuthProvider>
        <Header />
        <main className="page">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/futures" element={<Futures />} />
            <Route path="/defi" element={<Defi />} />
            <Route path="/bot" element={<Bot />} />
            <Route path="/news" element={<News />} />
            <Route path="/wallet" element={<Wallet />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </main>
        <Footer />
      </AuthProvider>
    </I18nProvider>
  );
}
