import type { Dispatch, FormEvent, SetStateAction } from 'react';
import { CircleAlert, Clock3, Pencil, Save, Search, Trash2, UserPlus, X } from 'lucide-react';

import type { AdminUser, UserFormState } from '../types';
import { formatDate } from '../utils';

type UsersPanelProps = {
  isLoading: boolean;
  users: AdminUser[];
  currentUserId?: string;
  currentUserEmail?: string | null;
  searchTerm: string;
  userForm: UserFormState;
  isSavingUser: boolean;
  setSearchTerm: (value: string) => void;
  setUserForm: Dispatch<SetStateAction<UserFormState>>;
  onSelectUser: (item: AdminUser) => void;
  onDeleteUser: (item: AdminUser) => void;
  onResetUserForm: () => void;
  onSubmitUser: (event: FormEvent<HTMLFormElement>) => void;
};

export function UsersPanel({
  isLoading,
  users,
  currentUserId,
  currentUserEmail,
  searchTerm,
  userForm,
  isSavingUser,
  setSearchTerm,
  setUserForm,
  onSelectUser,
  onDeleteUser,
  onResetUserForm,
  onSubmitUser,
}: UsersPanelProps) {
  return (
    <section className="admin-page__layout admin-page__layout--management">
      <section className="admin-page__panel admin-page__panel--wide">
        <div className="admin-page__panel-head">
          <div>
            <span>Quan ly nguoi dung</span>
            <h2>Danh sach tai khoan</h2>
          </div>
          <div className="admin-page__search">
            <Search size={16} />
            <input
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
              placeholder="Tim email, ten, so dien thoai..."
            />
          </div>
        </div>

        {isLoading ? (
          <div className="admin-page__empty">
            <Clock3 size={18} />
            <span>Dang tai danh sach tai khoan...</span>
          </div>
        ) : users.length === 0 ? (
          <div className="admin-page__empty">
            <CircleAlert size={18} />
            <span>Khong co tai khoan phu hop de hien thi.</span>
          </div>
        ) : (
          <div className="admin-page__table-wrap">
            <table className="admin-page__table">
              <thead>
                <tr>
                  <th>Email</th>
                  <th>Ngay tao</th>
                  <th>Vai tro</th>
                  <th>Trang thai</th>
                  <th>Thao tac</th>
                </tr>
              </thead>
              <tbody>
                {users.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <div className="admin-page__user-cell">
                        <strong>{item.email}</strong>
                        {item.account_name ? <span>{item.account_name}</span> : null}
                        {item.email === currentUserEmail ? <span>Phien hien tai</span> : null}
                      </div>
                    </td>
                    <td>{formatDate(item.created_at)}</td>
                    <td>
                      <span className={`admin-page__pill ${item.is_superuser ? 'admin-page__pill--admin' : ''}`}>
                        {item.is_superuser ? 'Quan tri vien' : 'Nguoi dung'}
                      </span>
                    </td>
                    <td>
                      <span className={`admin-page__pill ${item.is_active ? 'admin-page__pill--active' : 'admin-page__pill--inactive'}`}>
                        {item.is_active ? 'Dang hoat dong' : 'Tam khoa'}
                      </span>
                    </td>
                    <td>
                      <div className="admin-page__row-actions">
                        <button
                          className="admin-page__icon-button"
                          type="button"
                          onClick={() => onSelectUser(item)}
                          title="Sua nguoi dung"
                        >
                          <Pencil size={16} />
                        </button>
                        <button
                          className="admin-page__icon-button admin-page__icon-button--danger"
                          type="button"
                          onClick={() => onDeleteUser(item)}
                          disabled={item.id === currentUserId}
                          title="Xoa nguoi dung"
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <aside className="admin-page__side">
        <section className="admin-page__panel">
          <div className="admin-page__panel-head">
            <div>
              <span>{userForm.id ? 'Cap nhat' : 'Tao moi'}</span>
              <h2>{userForm.id ? 'Thong tin tai khoan' : 'Tai khoan moi'}</h2>
            </div>
            <UserPlus size={20} />
          </div>

          <form className="admin-page__form" onSubmit={onSubmitUser}>
            <label>
              Email
              <input
                type="email"
                value={userForm.email}
                onChange={(event) => setUserForm((prev) => ({ ...prev, email: event.target.value }))}
                required
              />
            </label>
            <label>
              Mat khau {userForm.id ? '(de trong neu khong doi)' : ''}
              <input
                type="password"
                value={userForm.password}
                onChange={(event) => setUserForm((prev) => ({ ...prev, password: event.target.value }))}
                minLength={userForm.id ? undefined : 8}
                required={!userForm.id}
              />
            </label>
            <label>
              Ten hien thi
              <input
                value={userForm.account_name}
                onChange={(event) => setUserForm((prev) => ({ ...prev, account_name: event.target.value }))}
              />
            </label>
            <label>
              Email lien he
              <input
                type="email"
                value={userForm.contact_email}
                onChange={(event) => setUserForm((prev) => ({ ...prev, contact_email: event.target.value }))}
              />
            </label>
            <label>
              So dien thoai
              <input
                value={userForm.contact_phone}
                onChange={(event) => setUserForm((prev) => ({ ...prev, contact_phone: event.target.value }))}
              />
            </label>
            <label>
              Anh dai dien URL
              <input
                value={userForm.avatar_url}
                onChange={(event) => setUserForm((prev) => ({ ...prev, avatar_url: event.target.value }))}
              />
            </label>
            <div className="admin-page__toggle-row">
              <label>
                <input
                  type="checkbox"
                  checked={userForm.is_active}
                  onChange={(event) => setUserForm((prev) => ({ ...prev, is_active: event.target.checked }))}
                />
                Tai khoan hoat dong
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={userForm.is_superuser}
                  onChange={(event) => setUserForm((prev) => ({ ...prev, is_superuser: event.target.checked }))}
                />
                Quyen admin
              </label>
            </div>
            <div className="admin-page__form-actions">
              <button className="admin-page__button admin-page__button--primary" type="submit" disabled={isSavingUser}>
                <Save size={17} />
                {isSavingUser ? 'Dang luu...' : 'Luu tai khoan'}
              </button>
              <button className="admin-page__button admin-page__button--ghost" type="button" onClick={onResetUserForm}>
                <X size={17} />
                Lam trong
              </button>
            </div>
          </form>
        </section>
      </aside>
    </section>
  );
}
