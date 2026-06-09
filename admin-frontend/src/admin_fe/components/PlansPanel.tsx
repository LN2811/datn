import type { Dispatch, FormEvent, SetStateAction } from 'react';
import { CircleAlert, Clock3, Pencil, Save, Sparkles, X } from 'lucide-react';

import type { PlanFormState, PricingPlan } from '../types';
import { formatLimit, formatNumber, formatVnd } from '../utils';

type PlansPanelProps = {
  isLoading: boolean;
  plans: PricingPlan[];
  activePlans: number;
  planForm: PlanFormState;
  isSavingPlan: boolean;
  setPlanForm: Dispatch<SetStateAction<PlanFormState>>;
  onSelectPlan: (item: PricingPlan) => void;
  onResetPlanForm: () => void;
  onSubmitPlan: (event: FormEvent<HTMLFormElement>) => void;
};

export function PlansPanel({
  isLoading,
  plans,
  activePlans,
  planForm,
  isSavingPlan,
  setPlanForm,
  onSelectPlan,
  onResetPlanForm,
  onSubmitPlan,
}: PlansPanelProps) {
  return (
    <section className="admin-page__layout admin-page__layout--management">
      <section className="admin-page__panel admin-page__panel--wide">
        <div className="admin-page__panel-head">
          <div>
            <span>Pricing plans</span>
            <h2>Danh sach goi nang cap</h2>
          </div>
          <div className="admin-page__plan-summary">
            <strong>{formatNumber(plans.length)}</strong>
            <span>{formatNumber(activePlans)} dang hien thi</span>
          </div>
        </div>

        {isLoading ? (
          <div className="admin-page__empty">
            <Clock3 size={18} />
            <span>Dang tai danh sach goi nang cap...</span>
          </div>
        ) : plans.length === 0 ? (
          <div className="admin-page__empty">
            <CircleAlert size={18} />
            <span>Chua co goi nang cap nao.</span>
          </div>
        ) : (
          <div className="admin-page__table-wrap">
            <table className="admin-page__table admin-page__table--plans">
              <thead>
                <tr>
                  <th>Goi</th>
                  <th>Gia</th>
                  <th>AI limit</th>
                  <th>Project</th>
                  <th>Chu ky</th>
                  <th>Trang thai</th>
                  <th>Thao tac</th>
                </tr>
              </thead>
              <tbody>
                {plans.map((item) => {
                  const maxProject = item.max_project ?? item.max_projects;
                  const badgeText = item.bagde_text ?? item.badge_text;

                  return (
                    <tr key={item.id} className={planForm.id === item.id ? 'admin-page__row--selected' : ''}>
                      <td>
                        <div className="admin-page__user-cell">
                          <strong>{item.name}</strong>
                          {item.description ? <span>{item.description}</span> : null}
                          {badgeText ? <span>{badgeText}</span> : null}
                        </div>
                      </td>
                      <td>{formatVnd(item.price)}</td>
                      <td>{formatLimit(item.ai_usage_limit, 'token')}</td>
                      <td>{formatLimit(maxProject, 'project')}</td>
                      <td>{item.billing_cycle || 'monthly'}</td>
                      <td>
                        <span className={`admin-page__pill ${item.is_active ? 'admin-page__pill--active' : 'admin-page__pill--inactive'}`}>
                          {item.is_active ? 'Dang bat' : 'Dang an'}
                        </span>
                        {item.is_featured ? <span className="admin-page__pill admin-page__pill--admin">Noi bat</span> : null}
                      </td>
                      <td>
                        <button
                          className="admin-page__edit-button"
                          type="button"
                          onClick={() => onSelectPlan(item)}
                          title="Sua goi nang cap"
                        >
                          <Pencil size={16} />
                          {planForm.id === item.id ? 'Dang sua' : 'Sua'}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <aside className="admin-page__side">
        <section className="admin-page__panel">
          <div className="admin-page__panel-head">
            <div>
              <span>{planForm.id ? 'Cap nhat' : 'Tao moi'}</span>
              <h2>{planForm.id ? 'Thong tin goi' : 'Goi nang cap moi'}</h2>
            </div>
            <Sparkles size={20} />
          </div>

          {planForm.id ? (
            <div className="admin-page__edit-state">
              <Pencil size={16} />
              <span>Dang sua goi AI. Bam Luu goi de cap nhat hoac Lam trong de tao goi moi.</span>
            </div>
          ) : null}

          <form className="admin-page__form" onSubmit={onSubmitPlan}>
            <label>
              Ten goi
              <input
                value={planForm.name}
                onChange={(event) => setPlanForm((prev) => ({ ...prev, name: event.target.value }))}
                required
              />
            </label>
            <label>
              Mo ta
              <textarea
                value={planForm.description}
                onChange={(event) => setPlanForm((prev) => ({ ...prev, description: event.target.value }))}
                rows={3}
              />
            </label>
            <div className="admin-page__form-grid">
              <label>
                Gia VND
                <input
                  type="number"
                  min="0"
                  step="1000"
                  value={planForm.price}
                  onChange={(event) => setPlanForm((prev) => ({ ...prev, price: event.target.value }))}
                  required
                />
              </label>
              <label>
                Chu ky
                <select
                  value={planForm.billing_cycle}
                  onChange={(event) => setPlanForm((prev) => ({ ...prev, billing_cycle: event.target.value }))}
                >
                  <option value="monthly">Monthly</option>
                  <option value="yearly">Yearly</option>
                  <option value="lifetime">Lifetime</option>
                </select>
              </label>
            </div>
            <div className="admin-page__form-grid">
              <label>
                AI usage limit
                <input
                  type="number"
                  min="0"
                  value={planForm.ai_usage_limit}
                  onChange={(event) => setPlanForm((prev) => ({ ...prev, ai_usage_limit: event.target.value }))}
                  placeholder="Trong de khong gioi han"
                />
              </label>
              <label>
                Max project
                <input
                  type="number"
                  min="0"
                  value={planForm.max_project}
                  onChange={(event) => setPlanForm((prev) => ({ ...prev, max_project: event.target.value }))}
                  placeholder="Trong de khong gioi han"
                />
              </label>
            </div>
            <div className="admin-page__form-grid">
              <label>
                Thu tu hien thi
                <input
                  type="number"
                  value={planForm.display_order}
                  onChange={(event) => setPlanForm((prev) => ({ ...prev, display_order: event.target.value }))}
                />
              </label>
              <label>
                Badge
                <input
                  value={planForm.bagde_text}
                  onChange={(event) => setPlanForm((prev) => ({ ...prev, bagde_text: event.target.value }))}
                  placeholder="Pho bien, Tot nhat..."
                />
              </label>
            </div>
            <div className="admin-page__toggle-row">
              <label>
                <input
                  type="checkbox"
                  checked={planForm.is_active}
                  onChange={(event) => setPlanForm((prev) => ({ ...prev, is_active: event.target.checked }))}
                />
                Hien thi goi
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={planForm.is_featured}
                  onChange={(event) => setPlanForm((prev) => ({ ...prev, is_featured: event.target.checked }))}
                />
                Goi noi bat
              </label>
            </div>
            <div className="admin-page__form-actions">
              <button className="admin-page__button admin-page__button--primary" type="submit" disabled={isSavingPlan}>
                <Save size={17} />
                {isSavingPlan ? 'Dang luu...' : 'Luu goi'}
              </button>
              <button className="admin-page__button admin-page__button--ghost" type="button" onClick={onResetPlanForm}>
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
