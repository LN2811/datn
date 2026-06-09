import type { AdminUser, PlanFormState, PricingPlan, TopUsageUser, UserFormState } from './types';

export const getErrorMessage = (error: unknown) => {
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

  return 'Khong xu ly duoc yeu cau quan tri.';
};

export const toFiniteNumber = (value?: number | null) => {
  const numericValue = Number(value ?? 0);
  return Number.isFinite(numericValue) ? numericValue : 0;
};

export const formatNumber = (value?: number | null) =>
  new Intl.NumberFormat('vi-VN').format(Math.round(toFiniteNumber(value)));

export const formatCurrency = (value?: number | null) =>
  new Intl.NumberFormat('vi-VN', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 4,
  }).format(toFiniteNumber(value));

export const formatVnd = (value?: number | null) =>
  new Intl.NumberFormat('vi-VN', {
    style: 'currency',
    currency: 'VND',
    maximumFractionDigits: 0,
  }).format(toFiniteNumber(value));

export const formatLimit = (value?: number | null, unit = '') => {
  if (value === null || value === undefined) {
    return 'Khong gioi han';
  }

  const suffix = unit ? ` ${unit}` : '';
  return `${formatNumber(value)}${suffix}`;
};

export const formatDate = (value?: string | null) => {
  if (!value) {
    return 'Chua co du lieu';
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return 'Chua co du lieu';
  }

  return new Intl.DateTimeFormat('vi-VN', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  }).format(date);
};

export const formatPaymentProvider = (provider: string) => {
  if (provider === 'card') {
    return 'The ngan hang';
  }

  if (provider === 'momo') {
    return 'MoMo';
  }

  return provider || 'Khac';
};

export const formatPaymentStatus = (status: string) => {
  if (status === 'paid') {
    return 'Thanh cong';
  }

  if (status === 'pending') {
    return 'Dang cho';
  }

  if (status === 'failed' || status === 'create_failed') {
    return 'That bai';
  }

  return status || 'Khong ro';
};

export const getPaymentStatusClass = (status: string) => {
  if (status === 'paid') {
    return 'admin-page__pill admin-page__pill--active';
  }

  if (status === 'failed' || status === 'create_failed') {
    return 'admin-page__pill admin-page__pill--inactive';
  }

  return 'admin-page__pill';
};

export const normalizeTopUser = (item: unknown): TopUsageUser | null => {
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

export const formFromUser = (item: AdminUser): UserFormState => ({
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

export const formFromPlan = (item: PricingPlan): PlanFormState => ({
  id: item.id,
  name: item.name,
  description: item.description ?? '',
  price: String(item.price ?? 0),
  ai_usage_limit: item.ai_usage_limit === null || item.ai_usage_limit === undefined ? '' : String(item.ai_usage_limit),
  billing_cycle: item.billing_cycle || 'monthly',
  max_project:
    item.max_project === null || item.max_project === undefined
      ? item.max_projects === null || item.max_projects === undefined
        ? ''
        : String(item.max_projects)
      : String(item.max_project),
  is_active: item.is_active,
  is_featured: item.is_featured,
  display_order: String(item.display_order ?? 0),
  bagde_text: item.bagde_text ?? item.badge_text ?? '',
});

export const buildUserPayload = (form: UserFormState) => {
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

export const buildPlanPayload = (form: PlanFormState) => ({
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
