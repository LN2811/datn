import { useState, type FormEvent } from 'react';
import {
  ArrowRight,
  BadgeCheck,
  KeyRound,
  Mail,
  Sparkles,
  UserPlus,
} from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { Eye, EyeOff } from 'lucide-react';

import { useAuth } from '@/auth/AuthContext';

import './RegisterForm.css';
import logo from '../../../assets/logo1.svg'

const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const validateRegisterInput = (
  email: string,
  password: string,
  confirmPassword: string,
  acceptedPolicy: boolean,
): string | null => {
  if (!email.trim()) {
    return 'Vui lòng nhập email.';
  }

  if (!emailRegex.test(email.trim())) {
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

  return null;
};

export function RegisterForm() {
  const navigate = useNavigate();
  const { register } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [acceptedPolicy, setAcceptedPolicy] = useState(false);
  const [error, setError] = useState('');
  const [status, setStatus] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showpassword, setshowpassword] = useState(false);
  const [showconfirmPassword, setshowconfirmPassword] = useState(false);


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
      setStatus('Đăng ký thành công.');
      setTimeout(() => {
        navigate('/login')
      }, 1000);
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
      <div
        className="register-page__glow register-page__glow--left"
        aria-hidden="true"
      />
      <div
        className="register-page__glow register-page__glow--right"
        aria-hidden="true"
      />

      <section className="register-page__layout">
        <aside className="register-page__hero">
          <Link className="register-page__brand" to="/">
            LOC Tracking
          </Link>

          <span className="register-page__eyebrow">Tạo tài khoản</span>
          <div className='logo-login'>
            <img src={logo} alt="logo" />
          </div>

          <div className="register-page__feature-list">
            <article className="register-page__feature">
              <div className="register-page__feature-icon">
                <UserPlus size={20} />
              </div>
              <div>
                <h2>Thông tin rõ ràng</h2>
                <p>Thông tin cần thiết được nhóm gọn trên một form duy nhất.</p>
              </div>
            </article>

            <article className="register-page__feature">
              <div className="register-page__feature-icon">
                <BadgeCheck size={20} />
              </div>
              <div>
                <h2>Kiểm tra dữ liệu</h2>
                <p>Email, mật khẩu và xác nhận mật khẩu đều được kiểm tra trước khi gửi.</p>
              </div>
            </article>

            <article className="register-page__feature">
              <div className="register-page__feature-icon">
                <Sparkles size={20} />
              </div>
              <div>
                <h2>Kết nối backend</h2>
                <p>Form này gọi API đăng ký và tạo phiên đăng nhập sau khi thành công.</p>
              </div>
            </article>
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

          <span className="register-page__form-kicker">Tạo tài khoản</span>
          <h2 className="register-page__form-title">Đăng ký</h2>
          <p className="register-page__form-text">
            Điền email và mật khẩu để tạo tài khoản người dùng thông thường.
          </p>

          <div className="register-page__info">
            Tài khoản đăng ký mới sẽ được tạo với quyền người dùng thường, không phải admin.
          </div>

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

            <div className="register-page__field-grid">
              <div className="register-page__field">
                <label className="register-page__label" htmlFor="registerPassword">
                  Mật khẩu
                </label>
                <div className="register-page__input-shell">
                  <KeyRound size={18} />
                  <input
                    id="registerPassword"
                    name="registerPassword"
                    type={showpassword ? 'text' : 'password'}
                    autoComplete="new-password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    className="register-page__input register-page__input--embedded"
                    placeholder="Tối thiểu 8 ký tự"
                    required
                  />
                  <button
                  type="button"
                  onClick={() =>setshowpassword(!showpassword)}
                  className="passWord-toggle"
                  >
                    {showpassword? <EyeOff size={18}/>:<Eye size={18}></Eye>}
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
                    type={showconfirmPassword ? 'text' : 'password'}
                    autoComplete="new-password"
                    value={confirmPassword}
                    onChange={(event) => setConfirmPassword(event.target.value)}
                    className="register-page__input register-page__input--embedded"
                    placeholder="Nhập lại mật khẩu"
                    required
                  />
                  <button type='button' onClick={() =>setshowconfirmPassword(!showconfirmPassword)} className='passWord-toggle'>
                    {showconfirmPassword? <EyeOff size={18}></EyeOff> : <Eye size={18}></Eye>}
                  </button>
                </div>
              </div>
            </div>

            <label className="register-page__checkbox">
              <input
                type="checkbox"
                checked={acceptedPolicy}
                onChange={(event) => setAcceptedPolicy(event.target.checked)}
              />
              <span>
                Tôi đồng ý với điều khoản sử dụng và tạo tài khoản người dùng thường.
              </span>
            </label>

            {error ? <p className="register-page__error">{error}</p> : null}
            {status ? <p className="register-page__status">{status}</p> : null}

            <button
              className="register-page__submit"
              type="submit"
              disabled={isSubmitting}
            >
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
