import { useState, type FormEvent } from 'react';
import { ArrowRight, Eye, EyeOff, KeyRound, Mail, UserPlus } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';

import { useAuth } from '@/auth/AuthContext';

import './RegisterForm.css';
import logo from '../../../assets/logo1.svg';

const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const validateRegisterInput = (
  email: string,
  password: string,
  confirmPassword: string,
  acceptedPolicy: boolean,
) => {
  const normalizedEmail = email.trim();

  if (!normalizedEmail) {
    return 'Vui lòng nhập email.';
  }
  
  if (!emailRegex.test(normalizedEmail)) {
    return 'Email không đúng định dạng.';
  }

  if (password.length < 8) {
    return 'Mật khẩu tối thiểu 8 ký tự.';
  }

  if (password !== confirmPassword) {
    return 'Xác nhận mật khẩu không khớp.';
  }

  if (!acceptedPolicy) {
    return 'Vui lòng đồng ý với điều khoản trước khi đăng ký.';
  }

  return '';
};

export function RegisterForm() {
  const navigate = useNavigate();
  const { register } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [acceptedPolicy, setAcceptedPolicy] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [error, setError] = useState('');
  const [status, setStatus] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError('');
    setStatus('');

    const validationError = validateRegisterInput(
      email,
      password,
      confirmPassword,
      acceptedPolicy,
    );

    if (validationError) {
      setError(validationError);
      return;
    }

    setIsSubmitting(true);
    try {
      await register(email.trim(), password);
      setStatus('Đăng ký thành công. Đang chuyển sang trang đăng nhập...');
      window.setTimeout(() => {
        navigate('/login', { replace: true });
      }, 800);
    } catch (submitError) {
      setError(
        submitError instanceof Error && submitError.message
          ? submitError.message
          : 'Đăng ký thất bại. Vui lòng thử lại.',
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="register-page">
      <section className="register-page__layout">
        <aside className="register-page__hero">
          <Link className="register-page__brand" to="/">
            LOC Tracking
          </Link>

          <div className="register-page__logo">
            <img src={logo} alt="LOC Tracking" />
          </div>

          <div className="register-page__feature">
            <UserPlus size={24} />
            <div>
              <h1>Tạo tài khoản</h1>
              <p>Đăng ký tài khoản user để bắt đầu quản lý project và bài học.</p>
            </div>
          </div>
        </aside>

        <section className="register-page__card">
          <div className="register-page__card-head">
            <Link className="register-page__back" to="/login">
              <ArrowRight size={16} />
              Sang trang đăng nhập
            </Link>

            <div className="register-page__badge">
              <Mail size={18} />
              Register
            </div>
          </div>

          <span className="register-page__form-kicker">Create account</span>
          <h2 className="register-page__form-title">Đăng ký</h2>
          <p className="register-page__form-text">
            Điền email và mật khẩu để tạo tài khoản user thông thường.
          </p>

          <form className="register-page__form" onSubmit={handleSubmit}>
            <div className="register-page__field">
              <label className="register-page__label" htmlFor="registerEmail">
                Email
              </label>
              <input
                id="registerEmail"
                name="registerEmail"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                className="register-page__input"
                placeholder="you@example.com"
                required
              />
            </div>

            <div className="register-page__field">
              <label className="register-page__label" htmlFor="registerPassword">
                Mật khẩu
              </label>
              <div className="register-page__input-shell">
                <KeyRound size={18} />
                <input
                  id="registerPassword"
                  name="registerPassword"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="new-password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  className="register-page__input register-page__input--embedded"
                  placeholder="Toi thieu 8 ky tu"
                  required
                />
                <button
                  type="button"
                  className="register-page__password-toggle"
                  onClick={() => setShowPassword((value) => !value)}
                  aria-label={showPassword ? 'An mat khau' : 'Hien mat khau'}
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            <div className="register-page__field">
              <label className="register-page__label" htmlFor="confirmPassword">
                Xác nhận mật khẩu
              </label>
              <div className="register-page__input-shell">
                <KeyRound size={18} />
                <input
                  id="confirmPassword"
                  name="confirmPassword"
                  type={showConfirmPassword ? 'text' : 'password'}
                  autoComplete="new-password"
                  value={confirmPassword}
                  onChange={(event) => setConfirmPassword(event.target.value)}
                  className="register-page__input register-page__input--embedded"
                  placeholder="Nhập lại mật khẩu"
                  required
                />
                <button
                  type="button"
                  className="register-page__password-toggle"
                  onClick={() => setShowConfirmPassword((value) => !value)}
                  aria-label={showConfirmPassword ? 'An mat khau' : 'Hien mat khau'}
                >
                  {showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            <label className="register-page__checkbox">
              <input
                type="checkbox"
                checked={acceptedPolicy}
                onChange={(event) => setAcceptedPolicy(event.target.checked)}
              />
              <span>Tôi đồng ý với điều khoản trước khi đăng ký tài khoản.</span>
            </label>

            {error ? <p className="register-page__error">{error}</p> : null}
            {status ? <p className="register-page__status">{status}</p> : null}

            <button className="register-page__submit" type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Đang xử lý...' : 'Đăng ký'}
            </button>
          </form>

          <p className="register-page__helper">
            Đã có tài khoản?
            <Link className="register-page__helper-link" to="/login">
              Đăng nhập ngay
            </Link>
          </p>
        </section>
      </section>
    </main>
  );
}
