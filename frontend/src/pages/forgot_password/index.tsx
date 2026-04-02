import { useState, type FormEvent } from 'react';
import {
  ArrowRight,
  Eye,
  EyeOff,
  KeyRound,
  LockKeyhole,
  MailCheck,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';

import { api } from '../../api/axios';
import './index.css';
import logo from '../../../assets/logo1.svg';

const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const getMessage = (error: unknown): string => {
  if (
    typeof error === 'object' &&
    error !== null &&
    'response' in error &&
    typeof (error as { response?: { data?: { detail?: unknown } } }).response?.data?.detail === 'string'
  ) {
    return (error as { response: { data: { detail: string } } }).response.data.detail;
  }

  if (error instanceof Error && error.message) {
    return error.message;
  }

  return 'Yeu cau that bai. Vui long thu lai.';
};

const validateEmail = (email: string): string | null => {
  const normalizedEmail = email.trim();

  if (!normalizedEmail) {
    return 'Vui long nhap email.';
  }

  if (!emailRegex.test(normalizedEmail)) {
    return 'Email khong dung dinh dang.';
  }

  return null;
};

const validatePassword = (password: string, confirmPassword: string): string | null => {
  if (password.length < 8) {
    return 'Mat khau toi thieu 8 ky tu.';
  }

  if (password !== confirmPassword) {
    return 'Mat khau xac nhan khong khop.';
  }

  return null;
};

export default function ForgotPasswordPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token')?.trim() ?? '';
  const isResetMode = token.length > 0;

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [resetLink, setResetLink] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const handleForgotPassword = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError('');
    setSuccess('');
    setResetLink('');

    const validationError = validateEmail(email);
    if (validationError) {
      setError(validationError);
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await api.post('/auth/forgot-password', { email: email.trim() });
      const payload = response.data as { message?: string; reset_link?: string } | undefined;
      setSuccess(payload?.message ?? 'Neu email ton tai, he thong da gui link dat lai mat khau.');
      setResetLink(payload?.reset_link ?? '');
    } catch (requestError) {
      setError(getMessage(requestError));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleResetPassword = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError('');
    setSuccess('');

    const validationError = validatePassword(password, confirmPassword);
    if (validationError) {
      setError(validationError);
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await api.post('/auth/reset-password', { token, password });
      const payload = response.data as { message?: string } | undefined;
      setSuccess(payload?.message ?? 'Dat lai mat khau thanh cong. Dang quay ve trang dang nhap...');
      window.setTimeout(() => {
        navigate('/login', { replace: true });
      }, 1200);
    } catch (requestError) {
      setError(getMessage(requestError));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="forgot-password-page">
      <div className="forgot-password-page__glow forgot-password-page__glow--left" aria-hidden="true" />
      <div className="forgot-password-page__glow forgot-password-page__glow--right" aria-hidden="true" />

      <section className="forgot-password-page__layout">
        <aside className="forgot-password-page__hero">
          <Link className="forgot-password-page__brand" to="/">
            LOC Tracking
          </Link>

          <div className="forgot-password-page__hero-copy">
            <span className="forgot-password-page__eyebrow">
              {isResetMode ? 'Account recovery' : 'Password support'}
            </span>
            <h1 className="forgot-password-page__hero-title">
              {isResetMode ? 'Tao mat khau moi va quay lai he thong.' : 'Khoi phuc tai khoan trong vai buoc.'}
            </h1>
            <p className="forgot-password-page__text forgot-password-page__text--hero">
              {isResetMode
                ? 'Link reset da xac thuc token. Ban chi can nhap mat khau moi va dang nhap lai.'
                : 'Nhap email da dang ky. He thong se tao link reset de ban dat lai mat khau nhanh hon.'}
            </p>
          </div>

          <div className="forgot-password-page__logo-shell">
            <img src={logo} alt="logo" />
          </div>

          <div className="forgot-password-page__feature-list">
            <article className="forgot-password-page__feature">
              <div className="forgot-password-page__feature-icon">
                <MailCheck size={20} />
              </div>
              <div>
                <h2>Nhap email</h2>
                <p>Xac dinh tai khoan can khoi phuc ma khong de lo thong tin nguoi dung.</p>
              </div>
            </article>

            <article className="forgot-password-page__feature">
              <div className="forgot-password-page__feature-icon">
                <ShieldCheck size={20} />
              </div>
              <div>
                <h2>Link reset an toan</h2>
                <p>Backend tao token reset rieng va chi chap nhan token hop le.</p>
              </div>
            </article>

            <article className="forgot-password-page__feature">
              <div className="forgot-password-page__feature-icon">
                <Sparkles size={20} />
              </div>
              <div>
                <h2>Quay lai dang nhap ngay</h2>
                <p>Sau khi cap nhat mat khau, trang se tu dong dua ban ve khu dang nhap.</p>
              </div>
            </article>
          </div>
        </aside>

        <section className="forgot-password-page__card">
          <div className="forgot-password-page__card-head">
            <Link className="forgot-password-page__back" to="/login">
              <ArrowRight size={16} />
              Quay ve dang nhap
            </Link>

            <div className="forgot-password-page__lock">
              {isResetMode ? <KeyRound size={22} /> : <LockKeyhole size={22} />}
            </div>
          </div>

          <span className="forgot-password-page__form-kicker">
            {isResetMode ? 'Reset access' : 'Forgot password'}
          </span>
          <h2 className="forgot-password-page__title">
            {isResetMode ? 'Dat lai mat khau' : 'Quen mat khau'}
          </h2>
          <p className="forgot-password-page__text">
            {isResetMode
              ? 'Nhap mat khau moi co do dai toi thieu 8 ky tu de kich hoat lai tai khoan.'
              : 'Form nay goi API `/auth/forgot-password`. O local, ban se nhan duoc reset link de test ngay.'}
          </p>

          <form
            className="forgot-password-page__form"
            onSubmit={isResetMode ? handleResetPassword : handleForgotPassword}
          >
            {!isResetMode ? (
              <label className="forgot-password-page__field" htmlFor="email">
                <span>Email</span>
                <input
                  id="email"
                  type="email"
                  autoComplete="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="you@example.com"
                />
              </label>
            ) : (
              <>
                <label className="forgot-password-page__field" htmlFor="password">
                  <span>Mat khau moi</span>
                  <div className="forgot-password-page__input-shell">
                    <input
                      id="password"
                      type={showPassword ? 'text' : 'password'}
                      autoComplete="new-password"
                      value={password}
                      onChange={(event) => setPassword(event.target.value)}
                      placeholder="Toi thieu 8 ky tu"
                    />
                    <button
                      type="button"
                      className="forgot-password-page__toggle"
                      onClick={() => setShowPassword((value) => !value)}
                      aria-label={showPassword ? 'An mat khau moi' : 'Hien mat khau moi'}
                    >
                      {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>
                </label>

                <label className="forgot-password-page__field" htmlFor="confirmPassword">
                  <span>Xac nhan mat khau</span>
                  <div className="forgot-password-page__input-shell">
                    <input
                      id="confirmPassword"
                      type={showConfirmPassword ? 'text' : 'password'}
                      autoComplete="new-password"
                      value={confirmPassword}
                      onChange={(event) => setConfirmPassword(event.target.value)}
                      placeholder="Nhap lai mat khau moi"
                    />
                    <button
                      type="button"
                      className="forgot-password-page__toggle"
                      onClick={() => setShowConfirmPassword((value) => !value)}
                      aria-label={showConfirmPassword ? 'An xac nhan mat khau' : 'Hien xac nhan mat khau'}
                    >
                      {showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>
                </label>
              </>
            )}

            {error ? (
              <p className="forgot-password-page__message forgot-password-page__message--error">{error}</p>
            ) : null}
            {success ? (
              <p className="forgot-password-page__message forgot-password-page__message--success">{success}</p>
            ) : null}

            {resetLink ? (
              <div className="forgot-password-page__dev-link">
                <span>Reset link (local):</span>
                <a href={resetLink}>{resetLink}</a>
              </div>
            ) : null}

            <button className="forgot-password-page__submit" type="submit" disabled={isSubmitting}>
              {isSubmitting
                ? 'Dang xu ly...'
                : isResetMode
                  ? 'Cap nhat mat khau'
                  : 'Gui link dat lai mat khau'}
            </button>
          </form>

          <p className="forgot-password-page__helper">
            {isResetMode
              ? 'Neu token het han, quay lai buoc truoc de tao link reset moi.'
              : 'Neu ban da nho lai mat khau, co the quay lai trang dang nhap ngay.'}
          </p>
        </section>
      </section>
    </main>
  );
}
