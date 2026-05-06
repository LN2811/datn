import { useEffect, useMemo, useState } from 'react';
import {
  ArrowLeft,
  CheckCircle2,
  CircleAlert,
  LogOut,
  Save,
  ShieldCheck,
} from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';

import { api } from '../api/axios.ts';
import { useAuth } from '../auth/AuthContext.tsx';

import './ProfilePage.css';

type ProfilePayload = {
  account_name: string | null;
  contact_email: string | null;
  contact_phone: string | null;
};

const getDisplayName = (accountName?: string | null, email?: string | null) => {
  if (accountName?.trim()) {
    return accountName.trim();
  }

  if (!email) {
    return 'Nguoi dung';
  }

  return email.split('@')[0]?.replace(/[._-]+/g, ' ') || email;
};

const getAvatarInitials = (name?: string | null, email?: string | null) => {
  const source = name?.trim() || email?.trim() || 'U';
  const chunks = source.includes('@')
    ? [source.charAt(0)]
    : source.split(/\s+/).filter(Boolean).slice(0, 2);

  return (
    chunks
      .map((chunk) => chunk.charAt(0).toUpperCase())
      .join('') || 'U'
  );
};

const getErrorMessage = (error: unknown) => {
  if (
    typeof error === 'object' &&
    error !== null &&
    'response' in error &&
    typeof (error as { response?: unknown }).response === 'object' &&
    (error as { response?: { data?: { detail?: unknown } } }).response?.data?.detail
  ) {
    const detail = (error as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
    if (typeof detail === 'string') {
      return detail;
    }
    if (Array.isArray(detail)) {
      return detail
        .map((item) => {
          if (typeof item === 'object' && item !== null && 'msg' in item) {
            return String((item as { msg: unknown }).msg);
          }
          return String(item);
        })
        .join(' ');
    }
  }

  if (error instanceof Error && error.message) {
    return error.message;
  }

  return 'Khong the cap nhat thong tin. Vui long thu lai.';
};

const emptyToNull = (value: string) => {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
};

export function ProfilePage() {
  const navigate = useNavigate();
  const { user, refreshUser, logout } = useAuth();

  const [accountName, setAccountName] = useState('');
  const [contactEmail, setContactEmail] = useState('');
  const [contactPhone, setContactPhone] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    setAccountName(user?.account_name ?? '');
    setContactEmail(user?.contact_email ?? '');
    setContactPhone(user?.contact_phone ?? '');
  }, [user]);

  const displayName = useMemo(
    () => getDisplayName(user?.account_name, user?.email),
    [user?.account_name, user?.email],
  );
  const avatarInitials = getAvatarInitials(displayName, user?.email);

  const handleSave = async () => {
    setIsSaving(true);
    setSuccessMessage('');
    setErrorMessage('');

    const payload: ProfilePayload = {
      account_name: emptyToNull(accountName),
      contact_email: emptyToNull(contactEmail),
      contact_phone: emptyToNull(contactPhone),
    };

    try {
      await api.patch('/users/me', payload);
      await refreshUser();
      setSuccessMessage('Da luu thay doi thong tin ca nhan.');
    } catch (saveError) {
      setErrorMessage(getErrorMessage(saveError));
    } finally {
      setIsSaving(false);
    }
  };

  const handleLogout = async () => {
    setIsLoggingOut(true);
    try {
      await logout();
      navigate('/login', { replace: true });
    } finally {
      setIsLoggingOut(false);
    }
  };

  return (
    <main className="profile-page">
      <section className="profile-page__shell">
        <header className="profile-page__topbar">
          <Link className="profile-page__back" to="/dashboard">
            <ArrowLeft size={18} />
            Dashboard
          </Link>
          {user?.is_superuser ? (
            <Link className="profile-page__admin" to="/admin">
              <ShieldCheck size={16} />
              Admin
            </Link>
          ) : null}
        </header>

        <section className="profile-page__card">
          <div className="profile-page__hero">
            {user?.avatar_url ? (
              <img className="profile-page__avatar" src={user.avatar_url} alt={displayName} />
            ) : (
              <div className="profile-page__avatar profile-page__avatar--initials">
                {avatarInitials}
              </div>
            )}
            <div>
              <span className="profile-page__eyebrow">Tai khoan ca nhan</span>
              <h1>{displayName}</h1>
              <p>{user?.email ?? 'Khong co email dang nhap'}</p>
            </div>
          </div>

          {successMessage ? (
            <div className="profile-page__banner profile-page__banner--success">
              <CheckCircle2 size={18} />
              <span>{successMessage}</span>
            </div>
          ) : null}

          {errorMessage ? (
            <div className="profile-page__banner profile-page__banner--error">
              <CircleAlert size={18} />
              <span>{errorMessage}</span>
            </div>
          ) : null}

          <form
            className="profile-page__form"
            onSubmit={(event) => {
              event.preventDefault();
              void handleSave();
            }}
          >
            <label className="profile-page__field" htmlFor="profile-account-name">
              <span>Ten hien thi</span>
              <input
                id="profile-account-name"
                type="text"
                value={accountName}
                onChange={(event) => setAccountName(event.target.value)}
                placeholder="Nhap ten hien thi"
              />
            </label>

            <label className="profile-page__field" htmlFor="profile-email">
              <span>Email dang nhap</span>
              <input id="profile-email" type="email" value={user?.email ?? ''} readOnly />
            </label>

            <label className="profile-page__field" htmlFor="profile-contact-email">
              <span>Email lien he</span>
              <input
                id="profile-contact-email"
                type="email"
                value={contactEmail}
                onChange={(event) => setContactEmail(event.target.value)}
                placeholder="contact@example.com"
              />
            </label>

            <label className="profile-page__field" htmlFor="profile-contact-phone">
              <span>So dien thoai</span>
              <input
                id="profile-contact-phone"
                type="tel"
                value={contactPhone}
                onChange={(event) => setContactPhone(event.target.value)}
                placeholder="Nhap so dien thoai lien he"
              />
            </label>

            <div className="profile-page__actions">
              <button className="profile-page__save" type="submit" disabled={isSaving}>
                <Save size={18} />
                {isSaving ? 'Dang luu...' : 'Luu thay doi'}
              </button>
              <Link className="profile-page__secondary" to="/dashboard">
                <ArrowLeft size={18} />
                Quay lai dashboard
              </Link>
              <button
                className="profile-page__logout"
                type="button"
                onClick={() => void handleLogout()}
                disabled={isLoggingOut}
              >
                <LogOut size={18} />
                {isLoggingOut ? 'Dang dang xuat...' : 'Dang xuat'}
              </button>
            </div>
          </form>
        </section>
      </section>
    </main>
  );
}
