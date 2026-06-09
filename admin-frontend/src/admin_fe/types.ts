import type { LucideIcon } from 'lucide-react';

export type AdminSection = 'users' | 'plans' | 'payments' | 'stats' | 'profile';

export type AdminUser = {
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

export type UsersResponse = {
  data: AdminUser[];
  count: number;
};

export type TopUsageUser = {
  user_id: string;
  total: number;
};

export type AIUsageStats = {
  total_tokens: number;
  total_cost: number;
  top_users: unknown[];
};

export type FeedbackStats = {
  total_feedbacks: number;
  avg_quality: number;
  avg_logic: number;
  avg_performance: number;
};

export type PeriodStat = {
  label: string;
  count: number;
};

export type PlanStat = {
  plan_id: string;
  plan_name: string;
  count: number;
};

export type PricingPlan = {
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

export type PaymentTransaction = {
  id: string;
  user_id: string;
  user_email?: string | null;
  plan_id: string;
  plan_name?: string | null;
  amount: number;
  currency: string;
  payment_provider: string;
  order_id: string;
  request_id: string;
  provider_transaction_id?: string | null;
  status: string;
  result_code?: number | null;
  message?: string | null;
  paid_at?: string | null;
  created_at?: string | null;
  update_at?: string | null;
};

export type PaymentsResponse = {
  items: PaymentTransaction[];
  total: number;
  limit: number;
  skip: number;
};

export type AdminStats = {
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

export type AdminData = {
  users: UsersResponse;
  plans: PricingPlan[];
  usage: AIUsageStats;
  feedback: FeedbackStats;
  stats: AdminStats;
  payments: PaymentsResponse;
};

export type UserFormState = {
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

export type ProfileFormState = {
  account_name: string;
  contact_email: string;
  contact_phone: string;
  avatar_url: string;
};

export type PlanFormState = {
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

export type StatCardItem = {
  label: string;
  value: string;
  detail: string;
  icon: LucideIcon;
  tone: string;
};
