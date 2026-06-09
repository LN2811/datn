import { useEffect, useState } from "react";
import { api } from "@/api/axios";
import "./upgrade.css";
import { X } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";

type PricingPlanFromApi = {
  id: string;
  name: string;
  description?: string | null;
  price: number;
  ai_usage_limit?: number | null;
  max_projects?: number | null;
  is_active: boolean;
};

type CurrentSubscriptionFromApi = {
  plan_id: string;
};

type PricingPlanCard = {
  id: string;
  title: string;
  subtitle?: string;
  priceText: string;
  description: string;
  highlighted?: boolean;
  features: string[];
};

function formatPrice(price: number) {
  if (price <= 0) {
    return "Miễn phí";
  }

  return new Intl.NumberFormat("vi-VN", {
    style: "currency",
    currency: "VND",
    maximumFractionDigits: 0,
  }).format(price);
}

function mapPlanToCard(plan: PricingPlanFromApi): PricingPlanCard {
  const name = plan.name.toLowerCase();
  const title = plan.name
    .replace(/chatgpt/gi, "Gói nâng cao")
    .replace(/codex/gi, "Gói nâng cao");

  return {
    id: plan.id,
    title: plan.name.includes("Business") ? "Doanh nghiệp" : title,
    subtitle: name.includes("nang-cao") || name.includes("premium")
      ? "Gói nâng cao"
      : undefined,
    priceText: formatPrice(plan.price),
    description: plan.description || "Gói dịch vụ học tập nâng cao.",
    highlighted: name.includes("premium") || name.includes("business"),
    features: [
      plan.ai_usage_limit
        ? `${plan.ai_usage_limit} lượt xử lý học tập`
        : "Không giới hạn theo cấu hình gói",
      plan.max_projects
        ? `Tối đa ${plan.max_projects} dự án`
        : "Không giới hạn dự án theo cấu hình gói",
      "Hỗ trợ tạo bài học từ tài liệu",
      "Hỗ trợ tạo câu hỏi và chấm điểm",
    ],
  };
}

export default function UpgradePlanPage() {
  const navigate = useNavigate();
  const [plans, setPlans] = useState<PricingPlanCard[]>([]);
  const [currentPlanId, setCurrentPlanId] = useState<string | null>(null);
  const [selectedPlanId, setSelectedPlanId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    const fetchPlans = async () => {
      try {
        setLoading(true);
        setError("");
        setSuccess("");

        const [plansResponse, subscriptionResponse] = await Promise.all([
          api.get<PricingPlanFromApi[]>("/pricing-plans"),
          api.get<CurrentSubscriptionFromApi | null>(
            "/pricing-plans/subscriptions/me/current",
          ),
        ]);

        const activePlans = plansResponse.data
          .filter((plan) => plan.is_active)
          .map(mapPlanToCard);

        setPlans(activePlans);
        setCurrentPlanId(subscriptionResponse.data?.plan_id ?? null);
      } catch {
        setError("Không thể tải danh sách gói dịch vụ.");
      } finally {
        setLoading(false);
      }
    };

    void fetchPlans();
  }, []);

  const handleSelectPlan = (plan: PricingPlanCard) => {
    if (selectedPlanId || plan.id === currentPlanId) {
      return;
    }

    setSelectedPlanId(plan.id);
    setError("");
    setSuccess("");
    navigate(`/order/${plan.id}`);
  };

  return (
    <div className="upgrade-overlay">
      <div className="upgrade-container">
        <Link to="/dashboard">
          <X className="outupgrade" size={30} />
        </Link>
        <header className="upgrade-header">
          <h1 className="upgrade-title">Nâng cấp gói dịch vụ</h1>
        </header>

        {loading ? <p className="upgrade-status">Đang tải gói dịch vụ...</p> : null}
        {error ? <p className="upgrade-error">{error}</p> : null}
        {success ? <p className="upgrade-success">{success}</p> : null}
        {!loading && plans.length > 0 ? (
          <section className="upgrade-grid">
            {plans.map((plan) => {
              const isCurrent = plan.id === currentPlanId;
              const isSelecting = plan.id === selectedPlanId;

              return (
                <article
                  key={plan.id}
                  className={[
                    "pricing-card",
                    plan.highlighted ? "pricing-card--highlighted" : "",
                    isCurrent ? "pricing-card--current" : "",
                  ].filter(Boolean).join(" ")}
                >
                  <div className="pricing-card__top">
                    <h2 className="pricing-card__title">{plan.title}</h2>

                    {plan.subtitle ? (
                      <p className="pricing-card__subtitle">{plan.subtitle}</p>
                    ) : null}

                    <div className="pricing-card__price">{plan.priceText}</div>

                    <p className="pricing-card__description">
                      {plan.description}
                    </p>

                    <button
                      type="button"
                      className="pricing-card__button"
                      disabled={isCurrent || Boolean(selectedPlanId)}
                      onClick={() => handleSelectPlan(plan)}
                    >
                      {isCurrent
                        ? "Gói hiện tại"
                        : isSelecting
                          ? "Đang chuyển..."
                          : "Chọn gói"}
                    </button>
                  </div>

                  <ul className="pricing-card__features">
                    {plan.features.map((feature) => (
                      <li key={feature} className="pricing-card__feature">
                        <span>*</span>
                        <span>{feature}</span>
                      </li>
                    ))}
                  </ul>
                </article>
              );
            })}
          </section>
        ) : null}
      </div>
    </div>
  );
}
