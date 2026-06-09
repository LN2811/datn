import { BarChart3, CreditCard, ShieldCheck, Sparkles, UsersRound } from 'lucide-react';

import type { AdminSection, PlanFormState, UserFormState } from './types';

export const emptyUserForm: UserFormState = {
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

export const emptyPlanForm: PlanFormState = {
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

export const currentYear = new Date().getFullYear();
export const availableYears = Array.from({ length: 5 }, (_, index) => currentYear - index);

export const tabItems = [
  { section: 'users' as AdminSection, icon: UsersRound, label: 'Quan ly nguoi dung' },
  { section: 'plans' as AdminSection, icon: Sparkles, label: 'Goi nang cap' },
  { section: 'payments' as AdminSection, icon: CreditCard, label: 'Danh sach mua goi' },
  { section: 'stats' as AdminSection, icon: BarChart3, label: 'Thong ke' },
  { section: 'profile' as AdminSection, icon: ShieldCheck, label: 'Thong tin admin' },
];
