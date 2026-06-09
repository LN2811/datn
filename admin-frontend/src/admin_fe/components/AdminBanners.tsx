import { CheckCircle2, CircleAlert } from 'lucide-react';

type AdminBannersProps = {
  error: string;
  notice: string;
};

export function AdminBanners({ error, notice }: AdminBannersProps) {
  return (
    <>
      {error ? (
        <div className="admin-page__banner admin-page__banner--error">
          <CircleAlert size={18} />
          <span>{error}</span>
        </div>
      ) : null}
      {notice ? (
        <div className="admin-page__banner admin-page__banner--success">
          <CheckCircle2 size={18} />
          <span>{notice}</span>
        </div>
      ) : null}
    </>
  );
}
