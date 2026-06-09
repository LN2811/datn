import { LogOut, RefreshCw } from 'lucide-react';

type AdminHeaderProps = {
  isLoading: boolean;
  isRefreshing: boolean;
  isLoggingOut: boolean;
  onRefresh: () => void;
  onLogout: () => void;
};

export function AdminHeader({
  isLoading,
  isRefreshing,
  isLoggingOut,
  onRefresh,
  onLogout,
}: AdminHeaderProps) {
  return (
    <header className="admin-page__topbar">
      <div className="admin-page__title">
        <span>Bang quan tri</span>
        <h1>Quan tri he thong hoc tap</h1>
        <p>Quan ly tai khoan, theo doi tang truong nguoi dung va cap nhat ho so admin.</p>
      </div>

      <div className="admin-page__actions">
        <button
          className="admin-page__button admin-page__button--ghost"
          type="button"
          onClick={onRefresh}
          disabled={isRefreshing || isLoading}
        >
          <RefreshCw size={18} className={isRefreshing ? 'admin-page__spin' : ''} />
          {isRefreshing ? 'Dang tai...' : 'Lam moi'}
        </button>
        <button
          className="admin-page__button admin-page__button--primary"
          type="button"
          onClick={onLogout}
          disabled={isLoggingOut}
        >
          <LogOut size={18} />
          {isLoggingOut ? 'Dang xu ly...' : 'Dang xuat'}
        </button>
      </div>
    </header>
  );
}
