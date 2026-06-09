import { Activity, BarChart3, CalendarDays, CheckCircle2, CircleAlert } from 'lucide-react';

import { availableYears } from '../constants';
import type { AdminStats, TopUsageUser } from '../types';
import { formatNumber } from '../utils';

type StatsPanelProps = {
  stats?: AdminStats;
  topUsers: TopUsageUser[];
  selectedYear: number;
  maxMonthlyRegistrations: number;
  maxQuarterUpdates: number;
  onChangeYear: (year: number) => void;
};

export function StatsPanel({
  stats,
  topUsers,
  selectedYear,
  maxMonthlyRegistrations,
  maxQuarterUpdates,
  onChangeYear,
}: StatsPanelProps) {
  return (
    <section className="admin-page__layout">
      <section className="admin-page__panel admin-page__panel--wide">
        <div className="admin-page__panel-head">
          <div>
            <span>Thong ke nguoi dung</span>
            <h2>Nguoi dung dang ky moi theo thang</h2>
          </div>
          <div className="admin-page__select-shell">
            <CalendarDays size={16} />
            <select value={selectedYear} onChange={(event) => onChangeYear(Number(event.target.value))}>
              {availableYears.map((year) => (
                <option key={year} value={year}>
                  Nam {year}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="admin-page__bar-chart">
          {(stats?.user_registrations_by_month ?? []).map((item) => (
            <div key={item.label} className="admin-page__bar-row">
              <span>{item.label}</span>
              <div className="admin-page__bar-track">
                <div style={{ width: `${Math.max(4, (item.count / maxMonthlyRegistrations) * 100)}%` }} />
              </div>
              <strong>{formatNumber(item.count)}</strong>
            </div>
          ))}
        </div>
      </section>

      <aside className="admin-page__side">
        <section className="admin-page__panel">
          <div className="admin-page__panel-head">
            <div>
              <span>Goi AI</span>
              <h2>Luot cap nhat theo quy</h2>
            </div>
            <BarChart3 size={20} />
          </div>
          <div className="admin-page__bar-chart admin-page__bar-chart--compact">
            {(stats?.subscription_updates_by_quarter ?? []).map((item) => (
              <div key={item.label} className="admin-page__bar-row">
                <span>{item.label}</span>
                <div className="admin-page__bar-track">
                  <div style={{ width: `${Math.max(4, (item.count / maxQuarterUpdates) * 100)}%` }} />
                </div>
                <strong>{formatNumber(item.count)}</strong>
              </div>
            ))}
          </div>
        </section>

        <section className="admin-page__panel">
          <div className="admin-page__panel-head">
            <div>
              <span>Phan bo goi</span>
              <h2>Goi dang hoat dong</h2>
            </div>
            <CheckCircle2 size={20} />
          </div>
          {(stats?.active_subscriptions_by_plan ?? []).length === 0 ? (
            <div className="admin-page__empty">
              <CircleAlert size={18} />
              <span>Chua co goi AI dang hoat dong.</span>
            </div>
          ) : (
            <div className="admin-page__rank-list">
              {(stats?.active_subscriptions_by_plan ?? []).map((item, index) => (
                <div key={item.plan_id} className="admin-page__rank-item">
                  <span>{index + 1}</span>
                  <div>
                    <strong>{item.plan_name}</strong>
                    <p>{formatNumber(item.count)} tai khoan</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="admin-page__panel">
          <div className="admin-page__panel-head">
            <div>
              <span>Top su dung</span>
              <h2>Token AI</h2>
            </div>
            <Activity size={20} />
          </div>
          {topUsers.length === 0 ? (
            <div className="admin-page__empty">
              <CircleAlert size={18} />
              <span>Chua co log su dung AI.</span>
            </div>
          ) : (
            <div className="admin-page__rank-list">
              {topUsers.map((item, index) => (
                <div key={`${item.user_id}-${index}`} className="admin-page__rank-item">
                  <span>{index + 1}</span>
                  <div>
                    <strong>{formatNumber(item.total)} token</strong>
                    <p>{item.user_id}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </aside>
    </section>
  );
}
