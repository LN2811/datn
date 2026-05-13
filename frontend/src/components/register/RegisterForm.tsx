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
    return 'Vui long nhap email.';
  }

  if (!emailRegex.test(normalizedEmail)) {
    return 'Email khong dung dinh dang.';
  }

  if (password.length < 8) {
    return 'Mat khau toi thieu 8 ky tu.';
  }

  if (password !== confirmPassword) {
    return 'Xac nhan mat khau khong khop.';
  }

  if (!acceptedPolicy) {
    return 'Vui long dong y voi dieu khoan truoc khi dang ky.';
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
      setStatus('Dang ky thanh cong. Dang chuyen sang trang dang nhap...');
      window.setTimeout(() => {
        navigate('/login', { replace: true });
      }, 800);
    } catch (submitError) {
      setError(
        submitError instanceof Error && submitError.message
          ? submitError.message
          : 'Dang ky that bai. Vui long thu lai.',
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
              <h1>Tao tai khoan</h1>
              <p>Dang ky tai khoan user de bat dau quan ly project va bai hoc.</p>
            </div>
          </div>
        </aside>

        <section className="register-page__card">
          <div className="register-page__card-head">
            <Link className="register-page__back" to="/login">
              <ArrowRight size={16} />
              Sang trang dang nhap
            </Link>

            <div className="register-page__badge">
              <Mail size={18} />
              Register
            </div>
          </div>

          <span className="register-page__form-kicker">Create account</span>
          <h2 className="register-page__form-title">Dang ky</h2>
          <p className="register-page__form-text">
            Dien email va mat khau de tao tai khoan user thong thuong.
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
                Mat khau
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
                Xac nhan mat khau
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
                  placeholder="Nhap lai mat khau"
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
              <span>Toi dong y voi dieu khoan su dung.</span>
            </label>

            {error ? <p className="register-page__error">{error}</p> : null}
            {status ? <p className="register-page__status">{status}</p> : null}

            <button className="register-page__submit" type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Dang xu ly...' : 'Dang ky'}
            </button>
          </form>

          <p className="register-page__helper">
            Da co tai khoan?
            <Link className="register-page__helper-link" to="/login">
              Dang nhap ngay
            </Link>
          </p>
        </section>
      </section>
    </main>
  );
}
