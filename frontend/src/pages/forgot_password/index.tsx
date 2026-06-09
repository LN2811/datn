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

  return 'Yêu cầu thất bại. Vui lòng thử lại.';
};

const validateEmail = (email: string): string | null => {
  const normalizedEmail = email.trim();

  if (!normalizedEmail) {
    return 'Vui lòng nhập email.';
  }

  if (!emailRegex.test(normalizedEmail)) {
    return 'Email không đúng định dạng.';
  }

  return null;
};

const validatePassword = (password: string, confirmPassword: string): string | null => {
  if (password.length < 8) {
    return 'Mat khau toi thieu 8 ky tu.';
  }

  if (password !== confirmPassword) {
    return 'Mật khẩu xác nhận không khớp.';
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
      setSuccess(payload?.message ?? 'Nếu email tồn tại, hệ thống đã gửi liên kết đặt lại mật khẩu.');
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
      setSuccess(payload?.message ?? 'Đặt lại mật khẩu thành công. Đang quay về trang đăng nhập...');
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
              {isResetMode ? 'Tạo mật khẩu mới.' : 'Khôi phục tài khoản trong vài bước.'}
            </h1>
            <p className="forgot-password-page__text forgot-password-page__text--hero">
              {isResetMode
                ? 'Link reset đã xác thực token. Bạn chỉ cần nhập mật khẩu mới và đăng nhập lại.'
                : 'Nhập email đã đăng ký. Hệ thống sẽ tạo link reset để bạn đặt lại mật khẩu nhanh hơn.'}
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
                <h2>Nhập email</h2>
                <p>Xác định tài khoản cần khôi phục mà không cần lo lắng về thông tin người dùng.</p>
              </div>
            </article>

            <article className="forgot-password-page__feature">
              <div className="forgot-password-page__feature-icon">
                <ShieldCheck size={20} />
              </div>
              <div>
                <h2>Link reset an toàn</h2>
                <p>Backend tào token reset riêng và chỉ chấp nhận token hợp lệ.</p>
              </div>
            </article>

            <article className="forgot-password-page__feature">
              <div className="forgot-password-page__feature-icon">
                <Sparkles size={20} />
              </div>
              <div>
                <h2>Quay lại đăng nhập ngay</h2>
                <p>Sau khi cập nhật mật khẩu, trang sẽ tự động đưa bạn về khu vực đăng nhập.</p>
              </div>
            </article>
          </div>
        </aside>

        <section className="forgot-password-page__card">
          <div className="forgot-password-page__card-head">
            <Link className="forgot-password-page__back" to="/login">
              <ArrowRight size={16} />
              Quay về đăng nhập
            </Link>

            <div className="forgot-password-page__lock">
              {isResetMode ? <KeyRound size={22} /> : <LockKeyhole size={22} />}
            </div>
          </div>

          <span className="forgot-password-page__form-kicker">
            {isResetMode ? 'Reset access' : 'Forgot password'}
          </span>
          <h2 className="forgot-password-page__title">
            {isResetMode ? 'Đặt lại mật khẩu' : 'Quên mật khẩu'}
          </h2>
          <p className="forgot-password-page__text">
            {isResetMode
              ? 'Nhập mật khẩu mới có độ dài tối thiểu 8 ký tự để kích hoạt lại tài khoản.'
              : 'Ở local, bạn sẽ nhận được link reset để test ngay.'}
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
                  <span>Mật khẩu mới</span>
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
                      aria-label={showPassword ? 'Ẩn mật khẩu mới' : 'Hiện mật khẩu mới'}
                    >
                      {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>
                </label>

                <label className="forgot-password-page__field" htmlFor="confirmPassword">
                  <span>Xác nhận mật khẩu</span>
                  <div className="forgot-password-page__input-shell">
                    <input
                      id="confirmPassword"
                      type={showConfirmPassword ? 'text' : 'password'}
                      autoComplete="new-password"
                      value={confirmPassword}
                      onChange={(event) => setConfirmPassword(event.target.value)}
                      placeholder="Nhập lại mật khẩu mới"
                    />
                    <button
                      type="button"
                      className="forgot-password-page__toggle"
                      onClick={() => setShowConfirmPassword((value) => !value)}
                      aria-label={showConfirmPassword ? 'Ẩn xác nhận mật khẩu' : 'Hiện xác nhận mật khẩu'}
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
                ? 'Đang xử lý...'
                : isResetMode
                  ? 'Cập nhật mật khẩu'
                  : 'Gửi link đặt lại mật khẩu'}
            </button>
          </form>

          <p className="forgot-password-page__helper">
            {isResetMode
              ? 'Nếu token hết hạn, quay lại bước trước để tạo link reset mới.'
              : 'Nếu bạn đã nhớ lại mật khẩu, có thể quay lại trang đăng nhập ngay.'}
          </p>
        </section>
      </section>
    </main>
  );
}
