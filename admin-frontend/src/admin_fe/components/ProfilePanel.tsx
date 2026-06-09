import type { Dispatch, FormEvent, SetStateAction } from 'react';
import { CheckCircle2, Save, ShieldCheck } from 'lucide-react';

import type { AdminUser, ProfileFormState } from '../types';
import { formatDate } from '../utils';

type ProfilePanelProps = {
  user?: AdminUser | null;
  profileForm: ProfileFormState;
  isSavingProfile: boolean;
  setProfileForm: Dispatch<SetStateAction<ProfileFormState>>;
  onSaveProfile: (event: FormEvent<HTMLFormElement>) => void;
};

export function ProfilePanel({
  user,
  profileForm,
  isSavingProfile,
  setProfileForm,
  onSaveProfile,
}: ProfilePanelProps) {
  return (
    <section className="admin-page__layout">
      <section className="admin-page__panel admin-page__panel--wide">
        <div className="admin-page__panel-head">
          <div>
            <span>Thong tin admin</span>
            <h2>Cap nhat ho so quan tri</h2>
          </div>
          <ShieldCheck size={20} />
        </div>

        <form className="admin-page__form admin-page__form--profile" onSubmit={onSaveProfile}>
          <label>
            Email dang nhap
            <input value={user?.email ?? ''} disabled />
          </label>
          <label>
            Ten hien thi
            <input
              value={profileForm.account_name}
              onChange={(event) => setProfileForm((prev) => ({ ...prev, account_name: event.target.value }))}
            />
          </label>
          <label>
            Email lien he
            <input
              type="email"
              value={profileForm.contact_email}
              onChange={(event) => setProfileForm((prev) => ({ ...prev, contact_email: event.target.value }))}
            />
          </label>
          <label>
            So dien thoai
            <input
              value={profileForm.contact_phone}
              onChange={(event) => setProfileForm((prev) => ({ ...prev, contact_phone: event.target.value }))}
            />
          </label>
          <label>
            Anh dai dien URL
            <input
              value={profileForm.avatar_url}
              onChange={(event) => setProfileForm((prev) => ({ ...prev, avatar_url: event.target.value }))}
            />
          </label>
          <button className="admin-page__button admin-page__button--primary" type="submit" disabled={isSavingProfile}>
            <Save size={17} />
            {isSavingProfile ? 'Dang luu...' : 'Luu thong tin admin'}
          </button>
        </form>
      </section>

      <aside className="admin-page__side">
        <section className="admin-page__panel admin-page__panel--status">
          <div className="admin-page__panel-head">
            <div>
              <span>Phien dang nhap</span>
              <h2>Trang thai admin</h2>
            </div>
            <CheckCircle2 size={20} />
          </div>

          <div className="admin-page__session">
            <div>
              <span>Email</span>
              <strong>{user?.email ?? 'admin'}</strong>
            </div>
            <div>
              <span>Vai tro</span>
              <strong>{user?.is_superuser ? 'Quan tri vien' : 'Nguoi dung'}</strong>
            </div>
            <div>
              <span>Ngay tao</span>
              <strong>{formatDate(user?.created_at)}</strong>
            </div>
            <div>
              <span>Truy cap</span>
              <strong>{user?.is_active ? 'Dang hoat dong' : 'Bi gioi han'}</strong>
            </div>
          </div>
        </section>
      </aside>
    </section>
  );
}
