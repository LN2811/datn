import { useEffect, useState } from "react";
import { api } from "@/api/axios";
import "./upgrade.css";

type PricingPlanFromApi = {
  id: string;
  name: string;
  description?: string | null;
  price: number;
  ai_usage_limit?: number | null;
  max_projects?: number | null;
  is_active: boolean;
};

type PricingPlanCard = {
  id: string;
  title: string;
  subtitle?: string;
  priceText: string;
  description: string;
  highlighted?: boolean;
  current?: boolean;
  features: string[];
};

function formatPrice(price: number) {
  if (price <= 0) {
    return "Usage pricing";
  }

  return new Intl.NumberFormat("vi-VN", {
    style: "currency",
    currency: "VND",
    maximumFractionDigits: 0,
  }).format(price);
}

function mapPlanToCard(plan: PricingPlanFromApi): PricingPlanCard {
  const name = plan.name.toLowerCase();

  return {
    id: plan.id,
    title: plan.name.includes("Business") ? "Business" : plan.name,
    subtitle: plan.name.includes("ChatGPT")
      ? "ChatGPT & Codex"
      : plan.name.includes("Codex")
        ? "Codex"
        : undefined,
    priceText: formatPrice(plan.price),
    description: plan.description || "Gói dịch vụ học tập với AI.",
    highlighted: name.includes("chatgpt") || name.includes("business"),
    features: [
      plan.ai_usage_limit
        ? `${plan.ai_usage_limit} lượt sử dụng AI`
        : "Không giới hạn theo cấu hình gói",
      plan.max_projects
        ? `Tối đa ${plan.max_projects} project`
        : "Không giới hạn project theo cấu hình gói",
      "Hỗ trợ tạo bài học từ tài liệu",
      "Hỗ trợ tạo câu hỏi và chấm điểm",
    ],
  };
}

export default function UpgradePlanPage() {
  const [activeTab, setActiveTab] = useState<"personal" | "business">("business");
  const [plans, setPlans] = useState<PricingPlanCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const fetchPlans = async () => {
      try {
        setLoading(true);
        setError("");

        const response = await api.get<PricingPlanFromApi[]>("/pricing-plans");

        const activePlans = response.data
          .filter((plan) => plan.is_active)
          .map(mapPlanToCard);

        setPlans(activePlans);
      } catch {
        setError("Không thể tải danh sách gói dịch vụ.");
      } finally {
        setLoading(false);
      }
    };

    fetchPlans();
  }, []);

  return (
    <div className="upgrade-overlay">
      <div className="upgrade-container">
        <header className="upgrade-header">
          <h1 className="upgrade-title">Nâng cấp gói dịch vụ</h1>

          <div className="upgrade-toggle">
            <button
              type="button"
              className={activeTab === "personal" ? "upgrade-toggle__item active" : "upgrade-toggle__item"}
              onClick={() => setActiveTab("personal")}
            >
              Cá nhân
            </button>

            <button
              type="button"
              className={activeTab === "business" ? "upgrade-toggle__item active" : "upgrade-toggle__item"}
              onClick={() => setActiveTab("business")}
            >
              Doanh nghiệp
            </button>
          </div>
        </header>

        {loading && <p className="upgrade-status">Đang tải gói dịch vụ...</p>}
        {error && <p className="upgrade-error">{error}</p>}

        {!loading && !error && (
          <section className="upgrade-grid">
            {plans.map((plan) => (
              <article
                key={plan.id}
                className={
                  plan.highlighted
                    ? "pricing-card pricing-card--highlighted"
                    : "pricing-card"
                }
              >
                <div className="pricing-card__top">
                  <h2 className="pricing-card__title">{plan.title}</h2>

                  {plan.subtitle && (
                    <p className="pricing-card__subtitle">{plan.subtitle}</p>
                  )}

                  <div className="pricing-card__price">{plan.priceText}</div>

                  <p className="pricing-card__description">
                    {plan.description}
                  </p>

                  <button type="button" className="pricing-card__button">
                    Chọn gói
                  </button>
                </div>

                <ul className="pricing-card__features">
                  {plan.features.map((feature) => (
                    <li key={feature} className="pricing-card__feature">
                      <span>✦</span>
                      <span>{feature}</span>
                    </li>
                  ))}
                </ul>
              </article>
            ))}
          </section>
        )}
      </div>
    </div>
  );
}