import { useEffect, useMemo, useState } from 'react';
import { ArrowLeft, CheckCircle2, Loader2, XCircle } from 'lucide-react';
import { Link, useSearchParams } from 'react-router-dom';

import { api } from '../api/axios';

import './MomoPaymentResultPage.css';

type PaymentStatus = {
  order_id: string;
  amount: number;
  status: 'pending' | 'paid' | 'failed' | 'create_failed' | string;
  result_code?: number | null;
  message?: string | null;
};

const getStatusText = (status?: string) => {
  switch (status) {
    case 'paid':
      return 'Thanh toán thành công';
    case 'failed':
    case 'create_failed':
      return 'Thanh toán thất bại';
    case 'pending':
      return 'Đang chờ xác nhận';
    default:
      return 'Đang kiểm tra thanh toán';
  }
};

export function MomoPaymentResultPage() {
  const [searchParams] = useSearchParams();
  const orderId = searchParams.get('orderId') || '';
  const momoMessage = searchParams.get('message') || '';
  const missingOrderError = orderId ? '' : 'Không tìm thấy mã đơn hàng MoMo.';
  const [paymentStatus, setPaymentStatus] = useState<PaymentStatus | null>(null);
  const [isLoading, setIsLoading] = useState(Boolean(orderId));
  const [error, setError] = useState('');

  useEffect(() => {
    if (!orderId) {
      return;
    }

    let isMounted = true;
    let pollCount = 0;

    const fetchStatus = async () => {
      try {
        const response = await api.get<PaymentStatus>(
          `/payments/momo/status/${orderId}`,
        );
        if (!isMounted) {
          return;
        }
        setPaymentStatus(response.data);
        setError('');
        if (response.data.status !== 'pending') {
          setIsLoading(false);
        }
      } catch {
        if (isMounted) {
          setError('Không thể kiểm tra trạng thái thanh toán.');
          setIsLoading(false);
        }
      }
    };

    void fetchStatus();
    const intervalId = window.setInterval(() => {
      pollCount += 1;
      if (pollCount >= 8 || paymentStatus?.status !== 'pending') {
        window.clearInterval(intervalId);
        setIsLoading(false);
        return;
      }
      void fetchStatus();
    }, 3000);

    return () => {
      isMounted = false;
      window.clearInterval(intervalId);
    };
  }, [orderId, paymentStatus?.status]);

  const isPaid = paymentStatus?.status === 'paid';
  const isFailed =
    paymentStatus?.status === 'failed' ||
    paymentStatus?.status === 'create_failed' ||
    Boolean(error || missingOrderError);

  const Icon = useMemo(() => {
    if (isPaid) {
      return CheckCircle2;
    }
    if (isFailed) {
      return XCircle;
    }
    return Loader2;
  }, [isPaid, isFailed]);

  return (
    <main className="momo-result">
      <section className="momo-result__card">
        <div
          className={[
            'momo-result__icon',
            isPaid ? 'momo-result__icon--success' : '',
            isFailed ? 'momo-result__icon--error' : '',
          ].filter(Boolean).join(' ')}
        >
          <Icon size={34} className={!isPaid && !isFailed ? 'momo-result__spin' : ''} />
        </div>

        <h1>{error || missingOrderError ? 'Không kiểm tra được thanh toán' : getStatusText(paymentStatus?.status)}</h1>
        <p>
          {error || missingOrderError || paymentStatus?.message || momoMessage || 'Hệ thống đang chờ MoMo xác nhận giao dịch.'}
        </p>

        {paymentStatus ? (
          <div className="momo-result__meta">
            <span>Mã đơn hàng</span>
            <strong>{paymentStatus.order_id}</strong>
            <span>Số tiền</span>
            <strong>
              {new Intl.NumberFormat('vi-VN', {
                style: 'currency',
                currency: 'VND',
                maximumFractionDigits: 0,
              }).format(paymentStatus.amount)}
            </strong>
          </div>
        ) : null}

        {isLoading ? (
          <p className="momo-result__hint">Đang đồng bộ trạng thái từ MoMo...</p>
        ) : null}

        <div className="momo-result__actions">
          <Link to="/upgrade" className="momo-result__button momo-result__button--secondary">
            <ArrowLeft size={18} />
            Quay lại gói dịch vụ
          </Link>
          <Link to="/dashboard" className="momo-result__button momo-result__button--primary">
            Về dashboard
          </Link>
        </div>
      </section>
    </main>
  );
}
