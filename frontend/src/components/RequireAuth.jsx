import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import Loading from './Loading.jsx';

// Wraps a route: visitors go to /login (and come back here afterwards);
// with `admin`, plain users go home.
export default function RequireAuth({ admin = false, children }) {
  const { user, ready, isAdmin } = useAuth();
  const location = useLocation();

  if (!ready) return <div className="wrap"><Loading /></div>;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname, reason: 'required' }} />;
  if (admin && !isAdmin) return <Navigate to="/" replace />;
  return children;
}
