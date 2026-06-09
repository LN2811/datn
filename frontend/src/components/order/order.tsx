import { useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  CheckCircle2,
  CreditCard,
  Loader2,
  ShieldCheck,
  Wallet,
} from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { api } from "@/api/axios";

import "./order.css";

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
  status?: string | null;
  message?: string | null;
};

type PaymentMethod = "momo" | "card";

const formatPrice = (price: number) => {
  if (price <= 0) {
    return "Miễn phí";
  }

  return new Intl.NumberFormat("vi-VN", {
    style: "currency",
    currency: "VND",
    maximumFractionDigits: 0,
  }).format(price);
};

const getErrorMessage = (error: unknown) => {
  if (!error || typeof error !== "object") {
    return "Không thể tạo thanh toán. Vui lòng thử lại.";
  }

  const source = error as {
    response?: { data?: { detail?: unknown } };
    message?: unknown;
  };

  if (typeof source.response?.data?.detail === "string") {
    return source.response.data.detail;
  }

  if (typeof source.message === "string") {
    return source.message;
  }

  return "Không thể tạo thanh toán. Vui lòng thử lại.";
};

export function OrderPage() {
  const { planId } = useParams();
  const navigate = useNavigate();
  const [plan, setPlan] = useState<PricingPlan | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [selectedPaymentMethod, setSelectedPaymentMethod] = useState<PaymentMethod>("momo");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    let isMounted = true;

    const fetchPlan = async () => {
      if (!planId) {
        setError("Không tìm thấy gói dịch vụ.");
        setIsLoading(false);
        return;
      }

      try {
        setIsLoading(true);
        setError("");
        const response = await api.get<PricingPlan[]>("/pricing-plans");
        const selectedPlan = response.data.find((item) => item.id === planId);

        if (!isMounted) {
          return;
        }

        if (!selectedPlan) {
          setError("Gói dịch vụ không tồn tại hoặc đã bị ẩn.");
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
        ? `${plan.ai_usage_limit} lượt xử lý học tập mỗi tháng`
        : "Không giới hạn lượt xử lý học tập theo cấu hình gói",
      plan.max_projects
        ? `Tối đa ${plan.max_projects} dự án`
        : "Không giới hạn số lượng dự án theo cấu hình gói",
      "Tạo bài học và câu hỏi từ tài liệu",
      "Theo dõi tiến độ học tập và kết quả bài làm",
    ];
  }, [plan]);

  const handleCreatePayment = async () => {
    if (!planId || !plan || isSubmitting) {
      return;
    }

    setIsSubmitting(true);
    setError("");
    setSuccess("");

    try {
      const endpoint =
        selectedPaymentMethod === "card" ? "/payments/card/create" : "/payments/momo/create";
      const response = await api.post<PaymentCreateResponse>(endpoint, {
        plan_id: planId,
      });
      const data = response.data;

      if (selectedPaymentMethod === "card" || data.status === "paid") {
        setSuccess(data.message || "Thanh toán bằng thẻ thành công.");
        window.setTimeout(() => {
          navigate("/dashboard", { replace: true });
        }, 900);
        return;
      }

      if (data.payment_required === false) {
        setSuccess(data.message || "Đăng ký gói thành công.");
        window.setTimeout(() => {
          navigate("/dashboard", { replace: true });
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

      setError("Không nhận được đường dẫn thanh toán.");
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
            Quay lại gói dịch vụ
          </Link>
        </div>

        <header className="order-header">
          <p>Thanh toán</p>
          <h1>Xác nhận gói dịch vụ</h1>
        </header>

        {isLoading ? (
          <div className="order-state">
            <Loader2 className="order-spin" size={20} />
            Đang tải thông tin gói...
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
                <span>Gói đã chọn</span>
                <h2>{plan.name}</h2>
                <p>{plan.description || "Gói dịch vụ học tập nâng cao."}</p>
              </div>

              <dl className="order-summary__meta">
                <div>
                  <dt>Trạng thái</dt>
                  <dd>{plan.is_active ? "Đang mở" : "Tạm khóa"}</dd>
                </div>
                <div>
                  <dt>Giá gói</dt>
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
              <h2>Phương thức thanh toán</h2>
              <div className="payment-methods">
                <button
                  type="button"
                  className={[
                    "payment-method",
                    selectedPaymentMethod === "momo" ? "payment-method--selected" : "",
                  ].filter(Boolean).join(" ")}
                  onClick={() => setSelectedPaymentMethod("momo")}
                >
                  <span className="payment-method__icon">
                    <Wallet size={22} />
                  </span>
                  <span>
                    <strong>MoMo</strong>
                    <small>Chuyển đến cổng MoMo để hoàn tất giao dịch.</small>
                  </span>
                </button>
                <button
                  type="button"
                  className={[
                    "payment-method",
                    selectedPaymentMethod === "card" ? "payment-method--selected" : "",
                  ].filter(Boolean).join(" ")}
                  onClick={() => setSelectedPaymentMethod("card")}
                >
                  <span className="payment-method__icon">
                    <CreditCard size={22} />
                  </span>
                  <span>
                    <strong>Thẻ ngân hàng</strong>
                    <small>Tạm thời xác nhận thành công ngay sau khi bấm thanh toán.</small>
                  </span>
                </button>
              </div>

              <div className="order-total">
                <span>Tổng thanh toán</span>
                <strong>{formatPrice(plan.price)}</strong>
              </div>

              <button
                type="button"
                className="order-submit"
                disabled={isSubmitting || !plan.is_active}
                onClick={handleCreatePayment}
              >
                {isSubmitting ? <Loader2 className="order-spin" size={18} /> : null}
                {isSubmitting
                  ? "Đang xử lý thanh toán..."
                  : selectedPaymentMethod === "card"
                    ? "Thanh toán bằng thẻ"
                    : "Thanh toán với MoMo"}
              </button>
            </aside>
          </section>
        ) : null}
      </div>
    </main>
  );
}
