import { useEffect, useState, type FormEvent } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { getHomePathByRole, useAuth } from '../auth/AuthContext.tsx';

const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const getMessage = (error: unknown): string => {
  if (error instanceof Error && error.message) {
    return error.message;
  }

  return 'Dang nhap that bai. Vui long thu lai.';
};

const getRequestedPath = (state: unknown): string | null => {
  if (
    typeof state === 'object' &&
    state !== null &&
    'from' in state &&
    typeof (state as { from?: unknown }).from === 'string'
  ) {
    const from = (state as { from: string }).from.trim();
    if (from.length > 0 && from !== '/login') {
      return from;
    }
  }

  return null;
};

const validateLoginInput = (email: string, password: string): string | null => {
  const normalizedEmail = email.trim();
  if (!normalizedEmail) {
    return 'Vui long nhap email.';
  }

  if (!emailRegex.test(normalizedEmail)) {
    return 'Email khong dung dinh dang.';
  }

  if (password.length < 6) {
    return 'Mat khau toi thieu 6 ky tu.';
  }

  return null;
};

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, login } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (user) {
      navigate(getHomePathByRole(user), { replace: true });
    }
  }, [navigate, user]);

  const requestedPath = getRequestedPath(location.state);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError('');

    const validationError = validateLoginInput(email, password);
    if (validationError) {
      setError(validationError);
      return;
    }

    setIsSubmitting(true);
    try {
      const currentUser = await login(email.trim(), password);
      navigate(requestedPath ?? getHomePathByRole(currentUser), { replace: true });
    } catch (submitError) {
      setError(getMessage(submitError));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="auth-shell">
      <section className="auth-card">
        <h1 className="auth-title">Dang nhap</h1>
        <p className="auth-muted">Nhap email va mat khau de tiep tuc.</p>

        <form className="auth-form" onSubmit={handleSubmit}>
          <label className="auth-label" htmlFor="email">
            Email
          </label>
          <input
            id="email"
            name="email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="auth-input"
            placeholder="you@example.com"
            required
          />

          <label className="auth-label" htmlFor="password">
            Mat khau
          </label>
          <input
            id="password"
            name="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="auth-input"
            placeholder="********"
            required
          />

          {error ? <p className="auth-error">{error}</p> : null}

          <button className="auth-button" type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Dang xu ly...' : 'Dang nhap'}
          </button>
        </form>
      </section>
    </main>
  );
}
