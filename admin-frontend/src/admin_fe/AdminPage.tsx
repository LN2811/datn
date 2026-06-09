import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react';
import { Activity, CreditCard, ShieldCheck, Sparkles, UsersRound } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

import { api } from '../api/axios.ts';
import { useAuth } from '../auth/AuthContext.tsx';
import { AdminBanners } from './components/AdminBanners';
import { AdminHeader } from './components/AdminHeader';
import { AdminTabs } from './components/AdminTabs';
import { PaymentsPanel } from './components/PaymentsPanel';
import { PlansPanel } from './components/PlansPanel';
import { ProfilePanel } from './components/ProfilePanel';
import { StatCards } from './components/StatCards';
import { StatsPanel } from './components/StatsPanel';
import { UsersPanel } from './components/UsersPanel';
import { currentYear, emptyPlanForm, emptyUserForm } from './constants';
import type {
  AIUsageStats,
  AdminData,
  AdminSection,
  AdminStats,
  AdminUser,
  FeedbackStats,
  PaymentsResponse,
  PlanFormState,
  PricingPlan,
  ProfileFormState,
  StatCardItem,
  TopUsageUser,
  UserFormState,
  UsersResponse,
} from './types';
import {
  buildPlanPayload,
  buildUserPayload,
  formFromPlan,
  formFromUser,
  formatCurrency,
  formatNumber,
  formatVnd,
  getErrorMessage,
  normalizeTopUser,
  toFiniteNumber,
} from './utils';

import './AdminPage.css';

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

  const loadAdminData = useCallback(async (year = selectedYear) => {
    const [
      usersResponse,
      plansResponse,
      usageResponse,
      feedbackResponse,
      statsResponse,
      paymentsResponse,
    ] = await Promise.all([
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
      api.get<PaymentsResponse>('/payments/admin/transactions', {
        params: { limit: 100 },
      }),
    ]);

    setData({
      users: usersResponse.data,
      plans: plansResponse.data,
      usage: usageResponse.data,
      feedback: feedbackResponse.data,
      stats: statsResponse.data,
      payments: paymentsResponse.data,
    });
  }, [selectedYear]);

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
  }, [loadAdminData]);

  useEffect(() => {
    setProfileForm({
      account_name: user?.account_name ?? '',
      contact_email: user?.contact_email ?? '',
      contact_phone: user?.contact_phone ?? '',
      avatar_url: user?.avatar_url ?? '',
    });
  }, [user]);

  const users = useMemo(() => data?.users.data ?? [], [data?.users.data]);
  const plans = useMemo(() => data?.plans ?? [], [data?.plans]);
  const paymentTransactions = useMemo(() => data?.payments.items ?? [], [data?.payments.items]);
  const totalUsers = data?.users.count ?? users.length;
  const activeUsers = data?.stats.totals.active_users ?? users.filter((item) => item.is_active).length;
  const adminUsers = data?.stats.totals.admin_users ?? users.filter((item) => item.is_superuser).length;
  const subscriptionUpdates = data?.stats.totals.subscription_updates ?? 0;
  const activePlans = plans.filter((item) => item.is_active).length;
  const paidPaymentCount = paymentTransactions.filter((item) => item.status === 'paid').length;
  const totalPaidAmount = paymentTransactions
    .filter((item) => item.status === 'paid')
    .reduce((total, item) => total + toFiniteNumber(item.amount), 0);

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

  const statCards: StatCardItem[] = [
    {
      label: 'Mua goi',
      value: formatVnd(totalPaidAmount),
      detail: `${formatNumber(paidPaymentCount)} giao dich thanh cong`,
      icon: CreditCard,
      tone: 'teal',
    },
    {
      label: 'Nguoi dung',
      value: formatNumber(totalUsers),
      detail: `${formatNumber(activeUsers)} tai khoan dang hoat dong`,
      icon: UsersRound,
      tone: 'blue',
    },
    {
      label: 'Admin',
      value: formatNumber(adminUsers),
      detail: 'Tai khoan co quyen quan tri he thong',
      icon: ShieldCheck,
      tone: 'teal',
    },
    {
      label: 'Token AI',
      value: formatNumber(data?.usage.total_tokens),
      detail: `Chi phi uoc tinh ${formatCurrency(data?.usage.total_cost)}`,
      icon: Activity,
      tone: 'amber',
    },
    {
      label: 'Cap nhat goi AI',
      value: formatNumber(subscriptionUpdates),
      detail: `Tong luot trong nam ${selectedYear}`,
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
      setNotice('Da lam moi du lieu quan tri.');
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
    setNotice(`Dang sua goi ${item.name}.`);
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
        throw new Error('Ten goi la bat buoc.');
      }
      if (!Number.isFinite(payload.price) || payload.price < 0) {
        throw new Error('Gia goi phai lon hon hoac bang 0.');
      }

      if (planForm.id) {
        await api.patch(`/pricing-plans/${planForm.id}`, payload);
        setNotice('Da cap nhat goi nang cap.');
      } else {
        await api.post('/pricing-plans', payload);
        setNotice('Da tao goi nang cap moi.');
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
        setNotice('Da cap nhat tai khoan nguoi dung.');
      } else {
        if (!userForm.password.trim()) {
          throw new Error('Mat khau la bat buoc khi tao tai khoan moi.');
        }
        await api.post('/users', buildUserPayload(userForm));
        setNotice('Da tao tai khoan nguoi dung moi.');
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
      setError('Khong the xoa tai khoan dang dang nhap.');
      return;
    }

    const confirmed = window.confirm(`Xoa tai khoan ${item.email}?`);
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
      setNotice('Da xoa tai khoan nguoi dung.');
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
      setNotice('Da cap nhat thong tin admin.');
    } catch (profileError) {
      setError(getErrorMessage(profileError));
    } finally {
      setIsSavingProfile(false);
    }
  };

  return (
    <main className="admin-page">
      <div className="admin-page__shell">
        <AdminHeader
          isLoading={isLoading}
          isRefreshing={isRefreshing}
          isLoggingOut={isLoggingOut}
          onRefresh={() => void handleRefresh()}
          onLogout={() => void handleLogout()}
        />

        <AdminTabs activeSection={activeSection} onChange={setActiveSection} />
        <AdminBanners error={error} notice={notice} />
        <StatCards cards={statCards} isLoading={isLoading} />

        {activeSection === 'users' ? (
          <UsersPanel
            isLoading={isLoading}
            users={filteredUsers}
            currentUserId={user?.id}
            currentUserEmail={user?.email}
            searchTerm={searchTerm}
            userForm={userForm}
            isSavingUser={isSavingUser}
            setSearchTerm={setSearchTerm}
            setUserForm={setUserForm}
            onSelectUser={handleSelectUser}
            onDeleteUser={(item) => void handleDeleteUser(item)}
            onResetUserForm={handleResetUserForm}
            onSubmitUser={(event) => void handleSubmitUser(event)}
          />
        ) : null}

        {activeSection === 'plans' ? (
          <PlansPanel
            isLoading={isLoading}
            plans={plans}
            activePlans={activePlans}
            planForm={planForm}
            isSavingPlan={isSavingPlan}
            setPlanForm={setPlanForm}
            onSelectPlan={handleSelectPlan}
            onResetPlanForm={handleResetPlanForm}
            onSubmitPlan={(event) => void handleSubmitPlan(event)}
          />
        ) : null}

        {activeSection === 'payments' ? (
          <PaymentsPanel
            isLoading={isLoading}
            transactions={paymentTransactions}
            users={users}
            plans={plans}
            total={data?.payments.total ?? paymentTransactions.length}
            paidPaymentCount={paidPaymentCount}
            totalPaidAmount={totalPaidAmount}
          />
        ) : null}

        {activeSection === 'stats' ? (
          <StatsPanel
            stats={data?.stats}
            topUsers={topUsers}
            selectedYear={selectedYear}
            maxMonthlyRegistrations={maxMonthlyRegistrations}
            maxQuarterUpdates={maxQuarterUpdates}
            onChangeYear={(year) => void handleChangeYear(year)}
          />
        ) : null}

        {activeSection === 'profile' ? (
          <ProfilePanel
            user={user}
            profileForm={profileForm}
            isSavingProfile={isSavingProfile}
            setProfileForm={setProfileForm}
            onSaveProfile={(event) => void handleSaveProfile(event)}
          />
        ) : null}
      </div>
    </main>
  );
}
