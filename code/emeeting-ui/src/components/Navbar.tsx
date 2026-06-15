// src/components/Navbar.tsx
import { Link } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { logout } from '../api/auth';
import { featureRoutes } from '../config/features';

const Navbar = () => {
  const { isAuthenticated, setAuth } = useAuthStore();

  const handleLogout = async () => {
    await logout();
    setAuth(null);
  };

  return (
    <nav>
      {featureRoutes
        .filter((f) => f.enabled && f.nav)
        .map((f) => (
          <Link key={f.key} to={f.nav!.to}>
            {f.nav!.label}
          </Link>
        ))}
      {isAuthenticated ? (
        <button className="action-btn" onClick={handleLogout}>Выйти</button>
      ) : (
        <Link className="action-btn" to="/login">Войти</Link>
      )}
    </nav>
  );
};

export default Navbar;