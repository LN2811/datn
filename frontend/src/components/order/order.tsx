import { useEffect, useMemo, useState } from 'react';
import {
  ArrowLeft,
  CheckCircle2,
  CreditCard,
  Loader2,
  ShieldCheck,
  Wallet,
} from 'lucide-react';
import { Link, useNavigate, useParams } from 'react-router-dom';

import { api } from '@/api/axios';

import './order.css';

type PricingPlan = {
  id: string;
  name: string;
  description?: string | null;
  price: number;
  ai_usage_limit?: number | null;
  max_projects?: number | null;
  is_active: boolean;
};

type PaymentCreateResponse = {
  payment_required?: boolean;
  pay_url?: string | null;
  deeplink?: string | null;
  order_id?: string | null;
  message?: string | null;
};

const formatPrice = (price: number) => {
  if (price <= 0) {
    return 'Free';
  }

  return new Intl.NumberFormat('vi-VN', {
    style: 'currency',
    currency: 'VND',
    maximumFractionDigits: 0,
  }).format(price);
};

const getErrorMessage = (error: unknown) => {
  if (!error || typeof error !== 'object') {
    return 'Khong the tao thanh toan. Vui long thu lai.';
  }

  const source = error as {
    response?: { data?: { detail?: unknown } };
    message?: unknown;
  };

  if (typeof source.response?.data?.detail === 'string') {
    return source.response.data.detail;
  }

  if (typeof source.message === 'string') {
    return source.message;
  }

  return 'Khong the tao thanh toan. Vui long thu lai.';
};

export function OrderPage() {
  const { planId } = useParams();
  const navigate = useNavigate();
  const [plan, setPlan] = useState<PricingPlan | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    let isMounted = true;

    const fetchPlan = async () => {
      if (!planId) {
        setError('Khong tim thay goi dich vu.');
        setIsLoading(false);
        return;
      }

      try {
        setIsLoading(true);
        setError('');
        const response = await api.get<PricingPlan[]>('/pricing-plans');
        const selectedPlan = response.data.find((item) => item.id === planId);

        if (!isMounted) {
          return;
        }

        if (!selectedPlan) {
          setError('Goi dich vu khong ton tai hoac da bi an.');
          setPlan(null);
          return;
        }

        setPlan(selectedPlan);
      } catch (requestError) {
        if (isMounted) {
          setError(getErrorMessage(requestError));
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    void fetchPlan();

    return () => {
      isMounted = false;
    };
  }, [planId]);

  const features = useMemo(() => {
    if (!plan) {
      return [];
    }

    return [
      plan.ai_usage_limit
        ? `${plan.ai_usage_limit} luot su dung AI`
        : 'Khong gioi han AI theo cau hinh goi',
      plan.max_projects
        ? `Toi da ${plan.max_projects} project`
        : 'Khong gioi han project theo cau hinh goi',
      'Tao bai hoc va cau hoi tu tai lieu',
      'Theo doi tien do hoc tap va ket qua bai lam',
    ];
  }, [plan]);

  const handleCreatePayment = async () => {
    if (!planId || !plan || isSubmitting) {
      return;
    }

    setIsSubmitting(true);
    setError('');
    setSuccess('');

    try {
      const response = await api.post<PaymentCreateResponse>('/payments/momo/create', {
        plan_id: planId,
      });
      const data = response.data;

      if (data.payment_required === false) {
        setSuccess(data.message || 'Dang ky goi thanh cong.');
        window.setTimeout(() => {
          navigate('/dashboard', { replace: true });
        }, 900);
        return;
      }

      const paymentUrl = data.pay_url || data.deeplink;
      if (paymentUrl) {
        window.location.href = paymentUrl;
        return;
      }

      if (data.order_id) {
        navigate(`/payment/momo/result?orderId=${encodeURIComponent(data.order_id)}`);
        return;
      }

      setError('MoMo khong tra ve duong dan thanh toan.');
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="order-page">
      <div className="order-shell">
        <div className="order-topbar">
          <Link className="order-back" to="/upgrade">
            <ArrowLeft size={18} />
            Quay lai goi dich vu
          </Link>
        </div>

        <header className="order-header">
          <p>Thanh toan</p>
          <h1>Xac nhan goi dich vu</h1>
        </header>

        {isLoading ? (
          <div className="order-state">
            <Loader2 className="order-spin" size={20} />
            Dang tai thong tin goi...
          </div>
        ) : null}

        {error ? (
          <div className="order-alert order-alert--error">
            <ShieldCheck size={20} />
            {error}
          </div>
        ) : null}

        {success ? (
          <div className="order-alert order-alert--success">
            <CheckCircle2 size={20} />
            {success}
          </div>
        ) : null}

        {plan ? (
          <section className="order-layout">
            <article className="order-summary">
              <div className="order-summary__icon">
                <Wallet size={28} />
              </div>
              <div className="order-summary__heading">
                <span>Goi da chon</span>
                <h2>{plan.name}</h2>
                <p>{plan.description || 'Goi dich vu hoc tap voi AI.'}</p>
              </div>

              <dl className="order-summary__meta">
                <div>
                  <dt>Trang thai</dt>
                  <dd>{plan.is_active ? 'Dang mo' : 'Tam khoa'}</dd>
                </div>
                <div>
                  <dt>Gia goi</dt>
                  <dd>{formatPrice(plan.price)}</dd>
                </div>
              </dl>

              <ul className="order-feature-list">
                {features.map((feature) => (
                  <li key={feature}>
                    <CheckCircle2 size={18} />
                    <span>{feature}</span>
                  </li>
                ))}
              </ul>
            </article>

            <aside className="order-payment">
              <h2>Phuong thuc thanh toan</h2>
              <div className="payment-methods">
                <button type="button" className="payment-method payment-method--selected">
                  <span className="payment-method__icon">
                    <CreditCard size={22} />
                  </span>
                  <span>
                    <strong>MoMo</strong>
                    <small>Chuyen den cong thanh toan MoMo de hoan tat giao dich.</small>
                  </span>
                </button>
              </div>

              <div className="order-total">
                <span>Tong thanh toan</span>
                <strong>{formatPrice(plan.price)}</strong>
              </div>

              <button
                type="button"
                className="order-submit"
                disabled={isSubmitting || !plan.is_active}
                onClick={handleCreatePayment}
              >
                {isSubmitting ? <Loader2 className="order-spin" size={18} /> : null}
                {isSubmitting ? 'Dang tao thanh toan...' : 'Thanh toan voi MoMo'}
              </button>
            </aside>
          </section>
        ) : null}
      </div>
    </main>
  );
}
