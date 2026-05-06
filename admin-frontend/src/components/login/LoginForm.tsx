import { useEffect, useState, type FormEvent } from 'react';
import {
  ArrowRight,
  LockKeyhole,
  ShieldCheck,
  Sparkles,
  UserRound,
} from 'lucide-react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { getHomePathByRole, useAuth } from '../../auth/AuthContext.tsx';
import { Eye, EyeOff } from 'lucide-react';
import './LoginForm.css';
import logo from '../../../assets/logo1.svg';
const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const getMessage = (error: unknown): string => {
  if (error instanceof Error && error.message) {
    return error.message;
  }

  return 'Đăng nhập thất bại. Vui lòng thử lại.';
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
    return 'Vui lòng nhập email.';
  }

  if (!emailRegex.test(normalizedEmail)) {
    return 'Email không đúng định dạng.';
  }

  if (password.length < 6) {
    return 'Mật khẩu tối thiểu 6 ký tự.';
  }

  return null;
};

export function LoginForm() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, login } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showpassword, setshowpassword] = useState(false);

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
    <main className="login-page">
      <div className="login-page__glow login-page__glow--left" aria-hidden="true" />
      <div className="login-page__glow login-page__glow--right" aria-hidden="true" />

      <section className="login-page__layout">
        <aside className="login-page__hero">
          <Link className="login-page__brand" to="/">
            LOC Tracking
          </Link>

          <span className="login-page__eyebrow">Nền tảng theo dõi tiến độ</span>
          <div className='logo-login'>
            <img src={logo} alt="logo" />
          </div>
          <div className="login-page__feature-list">
            <article className="login-page__feature">
              <div className="login-page__feature-icon">
                <ShieldCheck size={20} />
              </div>
              <div>
                <h2>Phân quyền rõ ràng</h2>
                <p>Mỗi tài khoản sẽ được điều hướng vào đúng khu vực làm việc.</p>
              </div>
            </article>

            <article className="login-page__feature">
              <div className="login-page__feature-icon">
                <Sparkles size={20} />
              </div>
              <div>
                <h2>Theo dõi LOC</h2>
                <p>Theo dõi kết quả nộp bài và tiến độ học tập rõ ràng hơn.</p>
              </div>
            </article>

            <article className="login-page__feature">
              <div className="login-page__feature-icon">
                <UserRound size={20} />
              </div>
              <div>
                <h2>Một điểm đăng nhập</h2>
                <p>Đăng nhập một lần để vào khu vực quản trị.</p>
              </div>
            </article>
          </div>
        </aside>

        <section className="login-page__card">
          <div className="login-page__card-head">
            <Link className="login-page__back" to="/">
              <ArrowRight size={16} />
              Quay về trang chính
            </Link>

            <div className="login-page__lock">
              <LockKeyhole size={22} />
            </div>
          </div>

          <span className="login-page__form-kicker">Truy cập tài khoản</span>
          <h2 className="login-page__form-title">Đăng nhập</h2>
          <p className="login-page__form-text">
            Nhập email và mật khẩu để tiếp tục vào hệ thống.
          </p>

          <form className="login-page__form" onSubmit={handleSubmit}>
            <div className="login-page__field">
              <label className="login-page__label" htmlFor="email">
                Email
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                className="login-page__input"
                placeholder="you@example.com"
                required
              />
            </div>

            <div className="login-page__field">
  <label className="login-page__label" htmlFor="password">
    Mật khẩu
  </label>

  <div className="login-page__input-shell">
    <input
      id="password"
      name="password"
      type={showpassword ? 'text' : 'password'}
      autoComplete="current-password"
      value={password}
      onChange={(event) => setPassword(event.target.value)}
      className="login-page__input login-page__input--embedded"
      placeholder="********"
      required
    />

    <button
      type="button"
      onClick={() => setshowpassword(!showpassword)}
      className="password-toggle"
    >
      {showpassword ? <EyeOff size={18} /> : <Eye size={18} />}
    </button>
  </div>
  <Link className='forgot_password' to="/forgot-password">
    Quên mật khẩu
  </Link>
</div>
            {error ? <p className="login-page__error">{error}</p> : null}

            <button
              className="login-page__submit"
              type="submit"
              disabled={isSubmitting}
            >
              {isSubmitting ? 'Đang xử lý...' : 'Đăng nhập'}
            </button>
          </form>

          <p className="login-page__helper">
            Sau khi đăng nhập, hệ thống sẽ tự động điều hướng đến khu vực phù hợp
            với vai trò của bạn.
          </p>
          <p className="login-page__helper login-page__helper--spaced">
            Chưa có tài khoản?
            <Link className="login-page__helper-link" to="/register">
              Mở trang đăng ký
            </Link>
          </p>
        </section>
      </section>
    </main>
  );
}
