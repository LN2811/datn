import { useEffect, useMemo, useState, type FormEvent } from 'react';
import {
  Activity,
  BarChart3,
  CalendarDays,
  CheckCircle2,
  CircleAlert,
  Clock3,
  LogOut,
  Pencil,
  RefreshCw,
  Save,
  Search,
  ShieldCheck,
  Sparkles,
  Trash2,
  UserPlus,
  UsersRound,
  X,
  type LucideIcon,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

import { api } from '../api/axios.ts';
import { useAuth } from '../auth/AuthContext.tsx';

import './AdminPage.css';

type AdminSection = 'users' | 'plans' | 'stats' | 'profile';

type AdminUser = {
  id: string;
  email: string;
  created_at?: string | null;
  account_name?: string | null;
  contact_email?: string | null;
  contact_phone?: string | null;
  avatar_url?: string | null;
  is_active: boolean;
  is_superuser: boolean;
};

type UsersResponse = {
  data: AdminUser[];
  count: number;
};

type TopUsageUser = {
  user_id: string;
  total: number;
};

type AIUsageStats = {
  total_tokens: number;
  total_cost: number;
  top_users: unknown[];
};

type FeedbackStats = {
  total_feedbacks: number;
  avg_quality: number;
  avg_logic: number;
  avg_performance: number;
};

type PeriodStat = {
  label: string;
  count: number;
};

type PlanStat = {
  plan_id: string;
  plan_name: string;
  count: number;
};

type PricingPlan = {
  id: string;
  name: string;
  description?: string | null;
  price: number;
  ai_usage_limit?: number | null;
  billing_cycle?: string | null;
  max_project?: number | null;
  max_projects?: number | null;
  is_active: boolean;
  is_featured: boolean;
  display_order: number;
  bagde_text?: string | null;
  badge_text?: string | null;
  created_at?: string | null;
  update_at?: string | null;
};

type AdminStats = {
  year: number;
  totals: {
    total_users: number;
    active_users: number;
    admin_users: number;
    subscription_updates: number;
  };
  user_registrations_by_month: PeriodStat[];
  subscription_updates_by_quarter: PeriodStat[];
  subscription_updates_by_plan: PlanStat[];
  active_subscriptions_by_plan: PlanStat[];
};

type AdminData = {
  users: UsersResponse;
  plans: PricingPlan[];
  usage: AIUsageStats;
  feedback: FeedbackStats;
  stats: AdminStats;
};

type UserFormState = {
  id: string | null;
  email: string;
  password: string;
  account_name: string;
  contact_email: string;
  contact_phone: string;
  avatar_url: string;
  is_active: boolean;
  is_superuser: boolean;
};

type ProfileFormState = {
  account_name: string;
  contact_email: string;
  contact_phone: string;
  avatar_url: string;
};

type PlanFormState = {
  id: string | null;
  name: string;
  description: string;
  price: string;
  ai_usage_limit: string;
  billing_cycle: string;
  max_project: string;
  is_active: boolean;
  is_featured: boolean;
  display_order: string;
  bagde_text: string;
};

const emptyUserForm: UserFormState = {
  id: null,
  email: '',
  password: '',
  account_name: '',
  contact_email: '',
  contact_phone: '',
  avatar_url: '',
  is_active: true,
  is_superuser: false,
};

const emptyPlanForm: PlanFormState = {
  id: null,
  name: '',
  description: '',
  price: '0',
  ai_usage_limit: '',
  billing_cycle: 'monthly',
  max_project: '',
  is_active: true,
  is_featured: false,
  display_order: '0',
  bagde_text: '',
};

const currentYear = new Date().getFullYear();
const availableYears = Array.from({ length: 5 }, (_, index) => currentYear - index);

const getErrorMessage = (error: unknown) => {
  if (
    typeof error === 'object' &&
    error !== null &&
    'response' in error &&
    typeof (error as { response?: unknown }).response === 'object'
  ) {
    const detail = (error as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
    if (typeof detail === 'string') {
      return detail;
    }
  }

  if (error instanceof Error && error.message) {
    return error.message;
  }

  return 'Không xử lý được yêu cầu quản trị.';
};

const toFiniteNumber = (value?: number | null) => {
  const numericValue = Number(value ?? 0);
  return Number.isFinite(numericValue) ? numericValue : 0;
};

const formatNumber = (value?: number | null) =>
  new Intl.NumberFormat('vi-VN').format(Math.round(toFiniteNumber(value)));

const formatCurrency = (value?: number | null) =>
  new Intl.NumberFormat('vi-VN', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 4,
  }).format(toFiniteNumber(value));

const formatVnd = (value?: number | null) =>
  new Intl.NumberFormat('vi-VN', {
    style: 'currency',
    currency: 'VND',
    maximumFractionDigits: 0,
  }).format(toFiniteNumber(value));

const formatLimit = (value?: number | null, unit = '') => {
  if (value === null || value === undefined) {
    return 'Không giới hạn';
  }

  const suffix = unit ? ` ${unit}` : '';
  return `${formatNumber(value)}${suffix}`;
};

const formatDate = (value?: string | null) => {
  if (!value) {
    return 'Chưa có dữ liệu';
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return 'Chưa có dữ liệu';
  }

  return new Intl.DateTimeFormat('vi-VN', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  }).format(date);
};

const normalizeTopUser = (item: unknown): TopUsageUser | null => {
  if (Array.isArray(item)) {
    const [userId, total] = item;
    return {
      user_id: String(userId ?? 'unknown'),
      total: Number(total ?? 0),
    };
  }

  if (typeof item === 'object' && item !== null) {
    const source = item as Record<string, unknown>;
    return {
      user_id: String(source.user_id ?? source[0] ?? 'unknown'),
      total: Number(source.total ?? source[1] ?? 0),
    };
  }

  return null;
};

const formFromUser = (item: AdminUser): UserFormState => ({
  id: item.id,
  email: item.email,
  password: '',
  account_name: item.account_name ?? '',
  contact_email: item.contact_email ?? '',
  contact_phone: item.contact_phone ?? '',
  avatar_url: item.avatar_url ?? '',
  is_active: item.is_active,
  is_superuser: item.is_superuser,
});

const formFromPlan = (item: PricingPlan): PlanFormState => ({
  id: item.id,
  name: item.name,
  description: item.description ?? '',
  price: String(item.price ?? 0),
  ai_usage_limit: item.ai_usage_limit === null || item.ai_usage_limit === undefined ? '' : String(item.ai_usage_limit),
  billing_cycle: item.billing_cycle || 'monthly',
  max_project:
    item.max_project === null || item.max_project === undefined ? '' : String(item.max_project),
  is_active: item.is_active,
  is_featured: item.is_featured,
  display_order: String(item.display_order ?? 0),
  bagde_text: item.bagde_text ?? item.badge_text ?? '',
});

const buildUserPayload = (form: UserFormState) => {
  const payload: Record<string, unknown> = {
    email: form.email.trim(),
    account_name: form.account_name.trim() || null,
    contact_email: form.contact_email.trim() || null,
    contact_phone: form.contact_phone.trim() || null,
    avatar_url: form.avatar_url.trim() || null,
    is_active: form.is_active,
    is_superuser: form.is_superuser,
  };

  if (form.password.trim()) {
    payload.password = form.password;
  }

  return payload;
};

const buildPlanPayload = (form: PlanFormState) => ({
  name: form.name.trim(),
  description: form.description.trim() || null,
  price: Number(form.price || 0),
  ai_usage_limit: form.ai_usage_limit.trim() ? Number(form.ai_usage_limit) : null,
  billing_cycle: form.billing_cycle,
  max_project: form.max_project.trim() ? Number(form.max_project) : null,
  is_active: form.is_active,
  is_featured: form.is_featured,
  display_order: form.display_order.trim() ? Number(form.display_order) : 0,
  bagde_text: form.bagde_text.trim() || null,
});

const tabItems: Array<{ section: AdminSection; icon: LucideIcon; label: string }> = [
  { section: 'users', icon: UsersRound, label: 'Quản lý người dùng' },
  { section: 'plans', icon: Sparkles, label: 'Gói nâng cấp' },
  { section: 'stats', icon: BarChart3, label: 'Thống kê' },
  { section: 'profile', icon: ShieldCheck, label: 'Thông tin admin' },
];

export function AdminPage() {
  const navigate = useNavigate();
  const { user, logout, refreshUser } = useAuth();

  const [activeSection, setActiveSection] = useState<AdminSection>('users');
  const [data, setData] = useState<AdminData | null>(null);
  const [selectedYear, setSelectedYear] = useState(currentYear);
  const [searchTerm, setSearchTerm] = useState('');
  const [userForm, setUserForm] = useState<UserFormState>(emptyUserForm);
  const [planForm, setPlanForm] = useState<PlanFormState>(emptyPlanForm);
  const [profileForm, setProfileForm] = useState<ProfileFormState>({
    account_name: '',
    contact_email: '',
    contact_phone: '',
    avatar_url: '',
  });
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isSavingUser, setIsSavingUser] = useState(false);
  const [isSavingPlan, setIsSavingPlan] = useState(false);
  const [isSavingProfile, setIsSavingProfile] = useState(false);
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');

  const loadAdminData = async (year = selectedYear) => {
    const [usersResponse, plansResponse, usageResponse, feedbackResponse, statsResponse] = await Promise.all([
      api.get<UsersResponse>('/users', {
        params: {
          page_size: 100,
          page_index: 1,
          sort_by: 'email',
          sort_order: 'asc',
        },
      }),
      api.get<PricingPlan[]>('/pricing-plans'),
      api.get<AIUsageStats>('/ai-usage-logs/admin/stats'),
      api.get<FeedbackStats>('/ai-code-feedback/admin/stats'),
      api.get<AdminStats>('/admin/stats', {
        params: { year },
      }),
    ]);

    setData({
      users: usersResponse.data,
      plans: plansResponse.data,
      usage: usageResponse.data,
      feedback: feedbackResponse.data,
      stats: statsResponse.data,
    });
  };

  useEffect(() => {
    let isMounted = true;

    const bootstrap = async () => {
      try {
        await loadAdminData(currentYear);
        if (isMounted) {
          setError('');
        }
      } catch (loadError) {
        if (isMounted) {
          setError(getErrorMessage(loadError));
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    void bootstrap();

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    setProfileForm({
      account_name: user?.account_name ?? '',
      contact_email: user?.contact_email ?? '',
      contact_phone: user?.contact_phone ?? '',
      avatar_url: user?.avatar_url ?? '',
    });
  }, [user]);

  const users = data?.users.data ?? [];
  const plans = data?.plans ?? [];
  const totalUsers = data?.users.count ?? users.length;
  const activeUsers = data?.stats.totals.active_users ?? users.filter((item) => item.is_active).length;
  const adminUsers = data?.stats.totals.admin_users ?? users.filter((item) => item.is_superuser).length;
  const subscriptionUpdates = data?.stats.totals.subscription_updates ?? 0;
  const activePlans = plans.filter((item) => item.is_active).length;
  const topUsers = useMemo(
    () => (data?.usage.top_users ?? []).map(normalizeTopUser).filter(Boolean) as TopUsageUser[],
    [data?.usage.top_users],
  );
  const filteredUsers = useMemo(() => {
    const keyword = searchTerm.trim().toLowerCase();
    if (!keyword) {
      return users;
    }

    return users.filter((item) =>
      [item.email, item.account_name, item.contact_email, item.contact_phone, item.id]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(keyword)),
    );
  }, [searchTerm, users]);

  const maxMonthlyRegistrations = Math.max(
    1,
    ...(data?.stats.user_registrations_by_month ?? []).map((item) => item.count),
  );
  const maxQuarterUpdates = Math.max(
    1,
    ...(data?.stats.subscription_updates_by_quarter ?? []).map((item) => item.count),
  );

  const statCards = [
    {
      label: 'Người dùng',
      value: formatNumber(totalUsers),
      detail: `${formatNumber(activeUsers)} tài khoản đang hoạt động`,
      icon: UsersRound,
      tone: 'blue',
    },
    {
      label: 'Admin',
      value: formatNumber(adminUsers),
      detail: 'Tài khoản có quyền quản trị hệ thống',
      icon: ShieldCheck,
      tone: 'teal',
    },
    {
      label: 'Token AI',
      value: formatNumber(data?.usage.total_tokens),
      detail: `Chi phí ước tính ${formatCurrency(data?.usage.total_cost)}`,
      icon: Activity,
      tone: 'amber',
    },
    {
      label: 'Cập nhật gói AI',
      value: formatNumber(subscriptionUpdates),
      detail: `Tổng lượt trong năm ${selectedYear}`,
      icon: Sparkles,
      tone: 'ink',
    },
  ];

  const handleRefresh = async () => {
    setIsRefreshing(true);
    setError('');
    setNotice('');

    try {
      await loadAdminData(selectedYear);
      setNotice('Đã làm mới dữ liệu quản trị.');
    } catch (refreshError) {
      setError(getErrorMessage(refreshError));
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleChangeYear = async (year: number) => {
    setSelectedYear(year);
    setIsRefreshing(true);
    setError('');
    setNotice('');

    try {
      await loadAdminData(year);
    } catch (yearError) {
      setError(getErrorMessage(yearError));
    } finally {
      setIsRefreshing(false);
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

  const handleSelectUser = (item: AdminUser) => {
    setUserForm(formFromUser(item));
    setNotice('');
    setError('');
  };

  const handleResetUserForm = () => {
    setUserForm(emptyUserForm);
    setNotice('');
    setError('');
  };

  const handleSelectPlan = (item: PricingPlan) => {
    setPlanForm(formFromPlan(item));
    setNotice('');
    setError('');
  };

  const handleResetPlanForm = () => {
    setPlanForm(emptyPlanForm);
    setNotice('');
    setError('');
  };

  const handleSubmitPlan = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSavingPlan(true);
    setNotice('');
    setError('');

    try {
      const payload = buildPlanPayload(planForm);
      if (!payload.name) {
        throw new Error('Tên gói là bắt buộc.');
      }
      if (!Number.isFinite(payload.price) || payload.price < 0) {
        throw new Error('Giá gói phải lớn hơn hoặc bằng 0.');
      }

      if (planForm.id) {
        await api.patch(`/pricing-plans/${planForm.id}`, payload);
        setNotice('Đã cập nhật gói nâng cấp.');
      } else {
        await api.post('/pricing-plans', payload);
        setNotice('Đã tạo gói nâng cấp mới.');
      }

      await loadAdminData(selectedYear);
      setPlanForm(emptyPlanForm);
    } catch (saveError) {
      setError(getErrorMessage(saveError));
    } finally {
      setIsSavingPlan(false);
    }
  };

  const handleSubmitUser = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSavingUser(true);
    setNotice('');
    setError('');

    try {
      if (userForm.id) {
        await api.patch(`/users/${userForm.id}`, buildUserPayload(userForm));
        setNotice('Đã cập nhật tài khoản người dùng.');
      } else {
        if (!userForm.password.trim()) {
          throw new Error('Mật khẩu là bắt buộc khi tạo tài khoản mới.');
        }
        await api.post('/users', buildUserPayload(userForm));
        setNotice('Đã tạo tài khoản người dùng mới.');
      }
      await loadAdminData(selectedYear);
      setUserForm(emptyUserForm);
    } catch (saveError) {
      setError(getErrorMessage(saveError));
    } finally {
      setIsSavingUser(false);
    }
  };

  const handleDeleteUser = async (item: AdminUser) => {
    if (item.id === user?.id) {
      setError('Không thể xóa tài khoản đang đăng nhập.');
      return;
    }

    const confirmed = window.confirm(`Xóa tài khoản ${item.email}?`);
    if (!confirmed) {
      return;
    }

    setNotice('');
    setError('');

    try {
      await api.delete(`/users/${item.id}`);
      await loadAdminData(selectedYear);
      if (userForm.id === item.id) {
        setUserForm(emptyUserForm);
      }
      setNotice('Đã xóa tài khoản người dùng.');
    } catch (deleteError) {
      setError(getErrorMessage(deleteError));
    }
  };

  const handleSaveProfile = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSavingProfile(true);
    setNotice('');
    setError('');

    try {
      await api.patch('/users/me', {
        account_name: profileForm.account_name.trim() || null,
        contact_email: profileForm.contact_email.trim() || null,
        contact_phone: profileForm.contact_phone.trim() || null,
        avatar_url: profileForm.avatar_url.trim() || null,
      });
      await refreshUser();
      await loadAdminData(selectedYear);
      setNotice('Đã cập nhật thông tin admin.');
    } catch (profileError) {
      setError(getErrorMessage(profileError));
    } finally {
      setIsSavingProfile(false);
    }
  };

  const renderUsersPanel = () => (
    <section className="admin-page__layout admin-page__layout--management">
      <section className="admin-page__panel admin-page__panel--wide">
        <div className="admin-page__panel-head">
          <div>
            <span>Quản lý người dùng</span>
            <h2>Danh sách tài khoản</h2>
          </div>
          <div className="admin-page__search">
            <Search size={16} />
            <input
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
              placeholder="Tìm email, tên, số điện thoại..."
            />
          </div>
        </div>

        {isLoading ? (
          <div className="admin-page__empty">
            <Clock3 size={18} />
            <span>Đang tải danh sách tài khoản...</span>
          </div>
        ) : filteredUsers.length === 0 ? (
          <div className="admin-page__empty">
            <CircleAlert size={18} />
            <span>Không có tài khoản phù hợp để hiển thị.</span>
          </div>
        ) : (
          <div className="admin-page__table-wrap">
            <table className="admin-page__table">
              <thead>
                <tr>
                  <th>Email</th>
                  <th>Ngày tạo</th>
                  <th>Vai trò</th>
                  <th>Trạng thái</th>
                  <th>Thao tác</th>
                </tr>
              </thead>
              <tbody>
                {filteredUsers.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <div className="admin-page__user-cell">
                        <strong>{item.email}</strong>
                        {item.account_name ? <span>{item.account_name}</span> : null}
                        {item.email === user?.email ? <span>Phiên hiện tại</span> : null}
                      </div>
                    </td>
                    <td>{formatDate(item.created_at)}</td>
                    <td>
                      <span
                        className={`admin-page__pill ${
                          item.is_superuser ? 'admin-page__pill--admin' : ''
                        }`}
                      >
                        {item.is_superuser ? 'Quản trị viên' : 'Người dùng'}
                      </span>
                    </td>
                    <td>
                      <span
                        className={`admin-page__pill ${
                          item.is_active ? 'admin-page__pill--active' : 'admin-page__pill--inactive'
                        }`}
                      >
                        {item.is_active ? 'Đang hoạt động' : 'Tạm khóa'}
                      </span>
                    </td>
                    <td>
                      <div className="admin-page__row-actions">
                        <button
                          className="admin-page__icon-button"
                          type="button"
                          onClick={() => handleSelectUser(item)}
                          title="Sửa người dùng"
                        >
                          <Pencil size={16} />
                        </button>
                        <button
                          className="admin-page__icon-button admin-page__icon-button--danger"
                          type="button"
                          onClick={() => void handleDeleteUser(item)}
                          disabled={item.id === user?.id}
                          title="Xóa người dùng"
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
              <span>{userForm.id ? 'Cập nhật' : 'Tạo mới'}</span>
              <h2>{userForm.id ? 'Thông tin tài khoản' : 'Tài khoản mới'}</h2>
            </div>
            <UserPlus size={20} />
          </div>

          <form className="admin-page__form" onSubmit={(event) => void handleSubmitUser(event)}>
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
              Mật khẩu {userForm.id ? '(để trống nếu không đổi)' : ''}
              <input
                type="password"
                value={userForm.password}
                onChange={(event) =>
                  setUserForm((prev) => ({ ...prev, password: event.target.value }))
                }
                minLength={userForm.id ? undefined : 8}
                required={!userForm.id}
              />
            </label>
            <label>
              Tên hiển thị
              <input
                value={userForm.account_name}
                onChange={(event) =>
                  setUserForm((prev) => ({ ...prev, account_name: event.target.value }))
                }
              />
            </label>
            <label>
              Email liên hệ
              <input
                type="email"
                value={userForm.contact_email}
                onChange={(event) =>
                  setUserForm((prev) => ({ ...prev, contact_email: event.target.value }))
                }
              />
            </label>
            <label>
              Số điện thoại
              <input
                value={userForm.contact_phone}
                onChange={(event) =>
                  setUserForm((prev) => ({ ...prev, contact_phone: event.target.value }))
                }
              />
            </label>
            <label>
              Ảnh đại diện URL
              <input
                value={userForm.avatar_url}
                onChange={(event) =>
                  setUserForm((prev) => ({ ...prev, avatar_url: event.target.value }))
                }
              />
            </label>
            <div className="admin-page__toggle-row">
              <label>
                <input
                  type="checkbox"
                  checked={userForm.is_active}
                  onChange={(event) =>
                    setUserForm((prev) => ({ ...prev, is_active: event.target.checked }))
                  }
                />
                Tài khoản hoạt động
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={userForm.is_superuser}
                  onChange={(event) =>
                    setUserForm((prev) => ({ ...prev, is_superuser: event.target.checked }))
                  }
                />
                Quyền admin
              </label>
            </div>
            <div className="admin-page__form-actions">
              <button className="admin-page__button admin-page__button--primary" type="submit" disabled={isSavingUser}>
                <Save size={17} />
                {isSavingUser ? 'Đang lưu...' : 'Lưu tài khoản'}
              </button>
              <button
                className="admin-page__button admin-page__button--ghost"
                type="button"
                onClick={handleResetUserForm}
              >
                <X size={17} />
                Làm trống
              </button>
            </div>
          </form>
        </section>
      </aside>
    </section>
  );

  const renderPlansPanel = () => (
    <section className="admin-page__layout admin-page__layout--management">
      <section className="admin-page__panel admin-page__panel--wide">
        <div className="admin-page__panel-head">
          <div>
            <span>Pricing plans</span>
            <h2>Danh sách gói nâng cấp</h2>
          </div>
          <div className="admin-page__plan-summary">
            <strong>{formatNumber(plans.length)}</strong>
            <span>{formatNumber(activePlans)} đang hiển thị</span>
          </div>
        </div>

        {isLoading ? (
          <div className="admin-page__empty">
            <Clock3 size={18} />
            <span>Đang tải danh sách gói nâng cấp...</span>
          </div>
        ) : plans.length === 0 ? (
          <div className="admin-page__empty">
            <CircleAlert size={18} />
            <span>Chưa có gói nâng cấp nào.</span>
          </div>
        ) : (
          <div className="admin-page__table-wrap">
            <table className="admin-page__table admin-page__table--plans">
              <thead>
                <tr>
                  <th>Gói</th>
                  <th>Gia</th>
                  <th>AI limit</th>
                  <th>Project</th>
                  <th>Chu kỳ</th>
                  <th>Trạng thái</th>
                  <th>Thao tác</th>
                </tr>
              </thead>
              <tbody>
                {plans.map((item) => {
                  const maxProject = item.max_project ?? item.max_projects;
                  const badgeText = item.bagde_text ?? item.badge_text;

                  return (
                    <tr key={item.id}>
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
                        <span
                          className={`admin-page__pill ${
                            item.is_active ? 'admin-page__pill--active' : 'admin-page__pill--inactive'
                          }`}
                        >
                          {item.is_active ? 'Đang bật' : 'Đang ẩn'}
                        </span>
                        {item.is_featured ? (
                          <span className="admin-page__pill admin-page__pill--admin">Nổi bật</span>
                        ) : null}
                      </td>
                      <td>
                        <button
                          className="admin-page__icon-button"
                          type="button"
                          onClick={() => handleSelectPlan(item)}
                          title="Sửa gói nâng cấp"
                        >
                          <Pencil size={16} />
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
              <span>{planForm.id ? 'Cập nhật' : 'Tạo mới'}</span>
              <h2>{planForm.id ? 'Thông tin gói' : 'Gói nâng cấp mới'}</h2>
            </div>
            <Sparkles size={20} />
          </div>

          <form className="admin-page__form" onSubmit={(event) => void handleSubmitPlan(event)}>
            <label>
              Tên gói
              <input
                value={planForm.name}
                onChange={(event) => setPlanForm((prev) => ({ ...prev, name: event.target.value }))}
                required
              />
            </label>
            <label>
              Mô tả
              <textarea
                value={planForm.description}
                onChange={(event) =>
                  setPlanForm((prev) => ({ ...prev, description: event.target.value }))
                }
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
                Chu kỳ
                <select
                  value={planForm.billing_cycle}
                  onChange={(event) =>
                    setPlanForm((prev) => ({ ...prev, billing_cycle: event.target.value }))
                  }
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
                  onChange={(event) =>
                    setPlanForm((prev) => ({ ...prev, ai_usage_limit: event.target.value }))
                  }
                  placeholder="Trống để không giới hạn"
                />
              </label>
              <label>
                Max project
                <input
                  type="number"
                  min="0"
                  value={planForm.max_project}
                  onChange={(event) =>
                    setPlanForm((prev) => ({ ...prev, max_project: event.target.value }))
                  }
                  placeholder="Trống để không giới hạn"
                />
              </label>
            </div>
            <div className="admin-page__form-grid">
              <label>
                Thứ tự hiển thị
                <input
                  type="number"
                  value={planForm.display_order}
                  onChange={(event) =>
                    setPlanForm((prev) => ({ ...prev, display_order: event.target.value }))
                  }
                />
              </label>
              <label>
                Badge
                <input
                  value={planForm.bagde_text}
                  onChange={(event) =>
                    setPlanForm((prev) => ({ ...prev, bagde_text: event.target.value }))
                  }
                  placeholder="Phổ biến, Tốt nhất..."
                />
              </label>
            </div>
            <div className="admin-page__toggle-row">
              <label>
                <input
                  type="checkbox"
                  checked={planForm.is_active}
                  onChange={(event) =>
                    setPlanForm((prev) => ({ ...prev, is_active: event.target.checked }))
                  }
                />
                Hiển thị gói
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={planForm.is_featured}
                  onChange={(event) =>
                    setPlanForm((prev) => ({ ...prev, is_featured: event.target.checked }))
                  }
                />
                Gói nổi bật
              </label>
            </div>
            <div className="admin-page__form-actions">
              <button className="admin-page__button admin-page__button--primary" type="submit" disabled={isSavingPlan}>
                <Save size={17} />
                {isSavingPlan ? 'Đang lưu...' : 'Lưu gói'}
              </button>
              <button
                className="admin-page__button admin-page__button--ghost"
                type="button"
                onClick={handleResetPlanForm}
              >
                <X size={17} />
                Làm trống
              </button>
            </div>
          </form>
        </section>
      </aside>
    </section>
  );

  const renderStatsPanel = () => (
    <section className="admin-page__layout">
      <section className="admin-page__panel admin-page__panel--wide">
        <div className="admin-page__panel-head">
          <div>
            <span>Thống kê người dùng</span>
            <h2>Người dùng đăng ký mới theo tháng</h2>
          </div>
          <div className="admin-page__select-shell">
            <CalendarDays size={16} />
            <select
              value={selectedYear}
              onChange={(event) => void handleChangeYear(Number(event.target.value))}
            >
              {availableYears.map((year) => (
                <option key={year} value={year}>
                  Năm {year}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="admin-page__bar-chart">
          {(data?.stats.user_registrations_by_month ?? []).map((item) => (
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
              <span>Gói AI</span>
              <h2>Lượt cập nhật theo quý</h2>
            </div>
            <BarChart3 size={20} />
          </div>
          <div className="admin-page__bar-chart admin-page__bar-chart--compact">
            {(data?.stats.subscription_updates_by_quarter ?? []).map((item) => (
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
              <span>Phân bổ gói</span>
              <h2>Gói đang hoạt động</h2>
            </div>
            <CheckCircle2 size={20} />
          </div>
          {(data?.stats.active_subscriptions_by_plan ?? []).length === 0 ? (
            <div className="admin-page__empty">
              <CircleAlert size={18} />
              <span>Chưa có gói AI đang hoạt động.</span>
            </div>
          ) : (
            <div className="admin-page__rank-list">
              {(data?.stats.active_subscriptions_by_plan ?? []).map((item, index) => (
                <div key={item.plan_id} className="admin-page__rank-item">
                  <span>{index + 1}</span>
                  <div>
                    <strong>{item.plan_name}</strong>
                    <p>{formatNumber(item.count)} tài khoản</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="admin-page__panel">
          <div className="admin-page__panel-head">
            <div>
              <span>Top sử dụng</span>
              <h2>Token AI</h2>
            </div>
            <Activity size={20} />
          </div>
          {topUsers.length === 0 ? (
            <div className="admin-page__empty">
              <CircleAlert size={18} />
              <span>Chưa có log sử dụng AI.</span>
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

  const renderProfilePanel = () => (
    <section className="admin-page__layout">
      <section className="admin-page__panel admin-page__panel--wide">
        <div className="admin-page__panel-head">
          <div>
            <span>Thông tin admin</span>
            <h2>Cập nhật hồ sơ quản trị</h2>
          </div>
          <ShieldCheck size={20} />
        </div>

        <form className="admin-page__form admin-page__form--profile" onSubmit={(event) => void handleSaveProfile(event)}>
          <label>
            Email đăng nhập
            <input value={user?.email ?? ''} disabled />
          </label>
          <label>
            Tên hiển thị
            <input
              value={profileForm.account_name}
              onChange={(event) =>
                setProfileForm((prev) => ({ ...prev, account_name: event.target.value }))
              }
            />
          </label>
          <label>
            Email liên hệ
            <input
              type="email"
              value={profileForm.contact_email}
              onChange={(event) =>
                setProfileForm((prev) => ({ ...prev, contact_email: event.target.value }))
              }
            />
          </label>
          <label>
            Số điện thoại
            <input
              value={profileForm.contact_phone}
              onChange={(event) =>
                setProfileForm((prev) => ({ ...prev, contact_phone: event.target.value }))
              }
            />
          </label>
          <label>
            Ảnh đại diện URL
            <input
              value={profileForm.avatar_url}
              onChange={(event) =>
                setProfileForm((prev) => ({ ...prev, avatar_url: event.target.value }))
              }
            />
          </label>
          <button className="admin-page__button admin-page__button--primary" type="submit" disabled={isSavingProfile}>
            <Save size={17} />
            {isSavingProfile ? 'Đang lưu...' : 'Lưu thông tin admin'}
          </button>
        </form>
      </section>

      <aside className="admin-page__side">
        <section className="admin-page__panel admin-page__panel--status">
          <div className="admin-page__panel-head">
            <div>
              <span>Phiên đăng nhập</span>
              <h2>Trạng thái admin</h2>
            </div>
            <CheckCircle2 size={20} />
          </div>

          <div className="admin-page__session">
            <div>
              <span>Email</span>
              <strong>{user?.email ?? 'admin'}</strong>
            </div>
            <div>
              <span>Vai trò</span>
              <strong>{user?.is_superuser ? 'Quản trị viên' : 'Người dùng'}</strong>
            </div>
            <div>
              <span>Ngày tạo</span>
              <strong>{formatDate(user?.created_at)}</strong>
            </div>
            <div>
              <span>Truy cập</span>
              <strong>{user?.is_active ? 'Đang hoạt động' : 'Bị giới hạn'}</strong>
            </div>
          </div>
        </section>
      </aside>
    </section>
  );

  return (
    <main className="admin-page">
      <div className="admin-page__shell">
        <header className="admin-page__topbar">
          <div className="admin-page__title">
            <span>Bảng quản trị</span>
            <h1>Quản trị hệ thống học tập</h1>
            <p>Quản lý tài khoản, theo dõi tăng trưởng người dùng và cập nhật hồ sơ admin.</p>
          </div>

          <div className="admin-page__actions">
            <button
              className="admin-page__button admin-page__button--ghost"
              type="button"
              onClick={() => void handleRefresh()}
              disabled={isRefreshing || isLoading}
            >
              <RefreshCw size={18} className={isRefreshing ? 'admin-page__spin' : ''} />
              {isRefreshing ? 'Đang tải...' : 'Làm mới'}
            </button>
            <button
              className="admin-page__button admin-page__button--primary"
              type="button"
              onClick={handleLogout}
              disabled={isLoggingOut}
            >
              <LogOut size={18} />
              {isLoggingOut ? 'Đang xử lý...' : 'Đăng xuất'}
            </button>
          </div>
        </header>

        <nav className="admin-page__tabs" aria-label="Chức năng quản trị">
          {tabItems.map(({ section, icon: Icon, label }) => (
            <button
              key={section}
              className={activeSection === section ? 'admin-page__tab admin-page__tab--active' : 'admin-page__tab'}
              type="button"
              onClick={() => setActiveSection(section)}
            >
              <Icon size={18} />
              {label}
            </button>
          ))}
        </nav>

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

        <section className="admin-page__grid admin-page__grid--stats">
          {statCards.map((card) => (
            <article key={card.label} className={`admin-page__stat admin-page__stat--${card.tone}`}>
              <div className="admin-page__stat-icon">
                <card.icon size={20} />
              </div>
              <span>{card.label}</span>
              <strong>{isLoading ? '-' : card.value}</strong>
              <p>{card.detail}</p>
            </article>
          ))}
        </section>

        {activeSection === 'users' ? renderUsersPanel() : null}
        {activeSection === 'plans' ? renderPlansPanel() : null}
        {activeSection === 'stats' ? renderStatsPanel() : null}
        {activeSection === 'profile' ? renderProfilePanel() : null}
      </div>
    </main>
  );
}
