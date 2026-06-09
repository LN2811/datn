import { CircleAlert, Clock3, CreditCard } from 'lucide-react';

import type { PaymentTransaction, PricingPlan, AdminUser } from '../types';
import {
  formatDate,
  formatNumber,
  formatPaymentProvider,
  formatPaymentStatus,
  formatVnd,
  getPaymentStatusClass,
} from '../utils';

type PaymentsPanelProps = {
  isLoading: boolean;
  transactions: PaymentTransaction[];
  users: AdminUser[];
  plans: PricingPlan[];
  total: number;
  paidPaymentCount: number;
  totalPaidAmount: number;
};

export function PaymentsPanel({
  isLoading,
  transactions,
  users,
  plans,
  total,
  paidPaymentCount,
  totalPaidAmount,
}: PaymentsPanelProps) {
  const getUserLabel = (item: PaymentTransaction) =>
    item.user_email ?? users.find((userItem) => userItem.id === item.user_id)?.email ?? item.user_id;

  const getPlanLabel = (item: PaymentTransaction) =>
    item.plan_name ?? plans.find((planItem) => planItem.id === item.plan_id)?.name ?? item.plan_id;

  return (
    <section className="admin-page__layout">
      <section className="admin-page__panel admin-page__panel--wide">
        <div className="admin-page__panel-head">
          <div>
            <span>Payments</span>
            <h2>Danh sach mua goi</h2>
          </div>
          <div className="admin-page__plan-summary">
            <strong>{formatNumber(total)}</strong>
            <span>{formatNumber(paidPaymentCount)} thanh cong</span>
          </div>
        </div>

        {isLoading ? (
          <div className="admin-page__empty">
            <Clock3 size={18} />
            <span>Dang tai danh sach mua goi...</span>
          </div>
        ) : transactions.length === 0 ? (
          <div className="admin-page__empty">
            <CircleAlert size={18} />
            <span>Chua co giao dich mua goi nao.</span>
          </div>
        ) : (
          <div className="admin-page__table-wrap">
            <table className="admin-page__table admin-page__table--payments">
              <thead>
                <tr>
                  <th>Nguoi mua</th>
                  <th>Goi</th>
                  <th>So tien</th>
                  <th>Phuong thuc</th>
                  <th>Trang thai</th>
                  <th>Ngay mua</th>
                  <th>Ma don</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <div className="admin-page__user-cell">
                        <strong>{getUserLabel(item)}</strong>
                        <span>{item.user_id}</span>
                      </div>
                    </td>
                    <td>
                      <div className="admin-page__user-cell">
                        <strong>{getPlanLabel(item)}</strong>
                        <span>{item.plan_id}</span>
                      </div>
                    </td>
                    <td>{formatVnd(item.amount)}</td>
                    <td>{formatPaymentProvider(item.payment_provider)}</td>
                    <td>
                      <span className={getPaymentStatusClass(item.status)}>
                        {formatPaymentStatus(item.status)}
                      </span>
                    </td>
                    <td>{formatDate(item.paid_at ?? item.created_at)}</td>
                    <td>
                      <span className="admin-page__mono">{item.order_id}</span>
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
              <span>Tong quan</span>
              <h2>Doanh thu thanh cong</h2>
            </div>
            <CreditCard size={20} />
          </div>
          <div className="admin-page__session">
            <div>
              <span>Tong tien</span>
              <strong>{formatVnd(totalPaidAmount)}</strong>
            </div>
            <div>
              <span>Giao dich thanh cong</span>
              <strong>{formatNumber(paidPaymentCount)}</strong>
            </div>
            <div>
              <span>Tong giao dich</span>
              <strong>{formatNumber(total)}</strong>
            </div>
          </div>
        </section>
      </aside>
    </section>
  );
}
