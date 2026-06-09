# Workflow 3: Điều phối AI giữa gói Free và Plus

## 1. Mục tiêu chức năng

Workflow này giải thích cách backend chọn AI provider/model dựa trên gói người dùng. Các chức năng AI chính không gọi thẳng Groq hoặc Cerebras trong từng service, mà đi qua `AITransactionService.chat`. Service này kiểm tra subscription, kiểm tra giới hạn token, chọn provider phù hợp, gọi AI, sau đó lưu usage log.

Điểm cần nói khi phản biện:

> Backend điều phối AI tập trung qua `AITransactionService`. Gói free mặc định dùng Groq. Gói plus/pro/premium hoặc gói có giá lớn hơn 0 sẽ dùng premium provider nếu server có `PREMIUM_AI_API_KEY`; nếu không có key premium thì fallback về Groq.

## 2. File liên quan

| File | Vai trò |
|---|---|
| `backend/app/services/ai_transaction.py` | Điều phối AI, chọn provider, kiểm tra limit, log usage |
| `backend/app/services/ai_provider_client.py` | Client gọi API theo chuẩn OpenAI-compatible |
| `backend/app/core/config.py` | Cấu hình key, base URL, model |
| `backend/app/services/user_subscriptions.py` | Kiểm tra subscription hiện tại |
| `backend/app/services/Pricing_plans.py` | Tạo/cập nhật plan, subscribe plan, check limit |
| `backend/app/models/models.py` | Model `PricingPlans`, `UserSubscriptions`, `AIUsageLogs` |

## 3. Flow tổng quát khi một chức năng gọi AI

```text
Service nghiệp vụ cần gọi AI
  -> AITransactionService.chat(...)
  -> _get_current_plan(db, user_id)
  -> _check_plan_limit(db, user_id, plan)
  -> _get_provider_config(plan)
  -> AIProviderService.chat(...)
  -> OpenAI-compatible API
  -> nhận content, model_name, tokens_used, provider
  -> _save_ai_usage_log(...)
  -> trả content về service nghiệp vụ
```

Các chức năng đang dùng kiểu gọi này gồm:

- Sinh curriculum/bài học.
- Sinh câu hỏi quiz.
- Chấm code GitHub.
- Một số flow phân tích/sinh nội dung mới.

## 4. Entry point điều phối AI

File:

```text
backend/app/services/ai_transaction.py
```

Hàm chính:

```python
AITransactionService.chat(
    db,
    user_id,
    project_id,
    action_type,
    messages,
    response_format=None,
    temperature=0.2,
    max_completion_tokens=None,
)
```

Ý nghĩa tham số:

| Tham số | Ý nghĩa |
|---|---|
| `db` | Session DB để lấy plan và log usage |
| `user_id` | Người đang dùng AI |
| `project_id` | Project liên quan, có thể null |
| `action_type` | Loại tác vụ AI, ví dụ `code_review`, `generate_questions` |
| `messages` | Prompt gửi sang model |
| `response_format` | Yêu cầu định dạng output, ví dụ JSON |
| `temperature` | Độ ngẫu nhiên |
| `max_completion_tokens` | Giới hạn token đầu ra |

## 5. Lấy gói hiện tại của user

Hàm:

```python
AITransactionService._get_current_plan(db, user_id)
```

Luồng:

```text
UserSubscriptions
  join PricingPlans
  -> user_id đúng user hiện tại
  -> start_date <= now hoặc start_date null
  -> end_date >= now hoặc end_date null
  -> PricingPlans.is_active == True
  -> order_by PricingPlans.created_at desc
  -> lấy plan đầu tiên
```

Nếu không có plan active, `_check_plan_limit` sẽ trả:

```text
403 No active subscription plan found.
```

Model liên quan:

```python
class PricingPlans(BaseModel, table=True):
    __tablename__ = "pricing_plans"
```

```python
class UserSubscriptions(BaseModel, table=True):
    __tablename__ = "user_subscriptions"
```

## 6. Kiểm tra giới hạn token

Hàm:

```python
AITransactionService._check_plan_limit(db, user_id, plan)
```

Luồng:

1. Nếu `plan is None`:

```text
403 No active subscription plan found.
```

2. Lấy giới hạn:

```python
limit = plan.ai_usage_limit
```

3. Nếu `limit is None` hoặc `limit <= 0`:

```text
Không giới hạn token AI
```

4. Nếu có limit, đếm token đã dùng trong tháng:

```python
used_tokens = AITransactionService._count_monthly_tokens(db, user_id)
```

5. Nếu:

```python
used_tokens >= limit
```

thì trả:

```text
403 AI usage limit reached for your current plan
```

## 7. Đếm token theo tháng

Hàm:

```python
AITransactionService._count_monthly_tokens(db, user_id)
```

Luồng:

```text
now
  -> start_of_month = ngày 1, 00:00:00
  -> sum(AIUsageLogs.tokens_used)
  -> where user_id = user hiện tại
  -> where created_at >= start_of_month
```

Model:

```python
class AIUsageLogs(BaseModel, table=True):
    __tablename__ = "ai_usage_log"
```

Các cột quan trọng:

| Cột | Ý nghĩa |
|---|---|
| `user_id` | User dùng AI |
| `project_id` | Project liên quan |
| `action_type` | Loại tác vụ |
| `tokens_used` | Số token provider trả về |
| `model_name` | Model thực tế provider trả về |
| `created_at` | Thời điểm gọi |

## 8. Chọn provider Free hay Plus

Hàm:

```python
AITransactionService._get_provider_config(plan)
```

Logic hiện tại:

```python
plan_name = plan.name.lower()
is_premium_plan = (
    any(keyword in plan_name for keyword in ("premium", "plus", "pro"))
    or plan.price > 0
)
```

Nếu:

```text
is_premium_plan == True
và có PREMIUM_AI_API_KEY
```

thì dùng premium provider.

Nếu không, dùng Groq.

Nói ngắn gọn:

| Trường hợp | Provider được chọn |
|---|---|
| Không có plan | Bị chặn trước đó bởi `_check_plan_limit` |
| Free, price = 0, tên không chứa plus/pro/premium | Groq |
| Plus/Pro/Premium và có `PREMIUM_AI_API_KEY` | Premium provider |
| Plus/Pro/Premium nhưng thiếu `PREMIUM_AI_API_KEY` | Groq fallback |
| Plan bất kỳ có `price > 0` và có `PREMIUM_AI_API_KEY` | Premium provider |

## 9. Cấu hình Groq

File:

```text
backend/app/core/config.py
```

Config:

```python
GROQ_API_KEY: str | None = None
GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
GROQ_MODEL: str = "llama-3.1-8b-instant"
```

Hàm tạo config:

```python
AITransactionService._get_groq_config()
```

Nếu thiếu key:

```text
400 GROQ API key is not configured.
```

Config trả về:

```python
AIProviderClient(
    provider="groq",
    api_key=settings.GROQ_API_KEY,
    base_url=settings.GROQ_BASE_URL,
    model=settings.GROQ_MODEL,
)
```

## 10. Cấu hình Plus/Premium

File:

```text
backend/app/core/config.py
```

Config:

```python
PREMIUM_AI_PROVIDER: str = "cerebras"
PREMIUM_AI_API_KEY: str | None = None
PREMIUM_AI_BASE_URL: str = "https://api.cerebras.ai/v1"
PREMIUM_AI_MODEL: str = "gpt-oss-120b"
```

Khi plan là plus/pro/premium hoặc `price > 0`, service tạo:

```python
AIProviderClient(
    provider=settings.PREMIUM_AI_PROVIDER,
    api_key=settings.PREMIUM_AI_API_KEY,
    base_url=settings.PREMIUM_AI_BASE_URL,
    model=settings.PREMIUM_AI_MODEL,
)
```

Điểm phản biện:

> Plus không được hard-code bằng plan id. Backend nhận diện bằng tên plan chứa `plus`, `pro`, `premium`, hoặc plan có `price > 0`.

## 11. Service gọi provider thật

File:

```text
backend/app/services/ai_provider_client.py
```

Hàm:

```python
AIProviderService.chat(config, messages, ...)
```

Luồng:

```text
AIProviderClient
  -> OpenAI(api_key=config.api_key, base_url=config.base_url)
  -> client.chat.completions.create(...)
  -> lấy response.choices[0].message.content
  -> lấy response.usage.total_tokens
  -> lấy response.model
  -> trả AIProviderResponse
```

Payload gửi provider:

```python
payload = {
    "model": config.model,
    "messages": messages,
    "temperature": temperature,
}
```

Nếu có:

```python
response_format
max_completion_tokens
```

thì thêm vào payload.

Lỗi provider:

| Lỗi | HTTP trả về |
|---|---|
| Rate limit | 429 |
| API error | 502 |
| Thiếu API key | 400 |

## 12. Lưu usage log sau khi gọi AI

Hàm:

```python
AITransactionService._save_ai_usage_log(...)
```

Tạo bản ghi:

```python
AIUsageLogs(
    user_id=user_id,
    project_id=project_id,
    action_type=action_type,
    model_name=provider_response.model_name,
    tokens_used=provider_response.tokens_used,
)
```

Ý nghĩa:

- Theo dõi user đã dùng bao nhiêu token.
- Biết tác vụ nào tiêu tốn token.
- Biết model thực tế provider trả về.
- Dùng dữ liệu này để kiểm tra limit tháng sau đó.

Các `action_type` thường gặp:

```text
generate_curriculum
generate_questions
generate_quiz_questions
code_review
generate_analysis
generate_feedback
```

## 13. Gói Free hoạt động thế nào

Điều kiện thường gặp:

```text
plan.name = free
plan.price = 0
plan.ai_usage_limit = giới hạn token của free hoặc null
```

Flow:

```text
User gọi chức năng AI
  -> _get_current_plan lấy plan free
  -> _check_plan_limit kiểm tra ai_usage_limit
  -> _get_provider_config thấy không phải premium
  -> _get_groq_config
  -> gọi Groq model llama-3.1-8b-instant
  -> lưu AIUsageLogs
```

Nếu free có `ai_usage_limit`, khi dùng hết token tháng thì bị chặn.

Nếu free có `ai_usage_limit = null` hoặc `<= 0`, code hiện hiểu là không giới hạn token.

## 14. Gói Plus hoạt động thế nào

Điều kiện thường gặp:

```text
plan.name chứa plus/pro/premium
hoặc plan.price > 0
```

Flow:

```text
User gọi chức năng AI
  -> _get_current_plan lấy plan plus
  -> _check_plan_limit kiểm tra ai_usage_limit
  -> _get_provider_config xác định premium plan
  -> nếu có PREMIUM_AI_API_KEY: dùng Cerebras/premium provider
  -> nếu không có PREMIUM_AI_API_KEY: fallback Groq
  -> gọi provider
  -> lưu AIUsageLogs
```

Điểm cần nói rõ:

> Muốn Plus thật sự dùng provider premium thì bắt buộc `.env` phải có `PREMIUM_AI_API_KEY`. Nếu thiếu key, dù plan là Plus thì code vẫn fallback về Groq.

## 15. Các endpoint liên quan đến gói

Route pricing:

```text
backend/app/api/route/Pricing_plans.py
```

Các endpoint quan trọng:

| Chức năng | Endpoint |
|---|---|
| Lấy danh sách gói | `GET /pricing-plans` |
| Tạo gói | `POST /pricing-plans` |
| Lấy subscription hiện tại | `GET /pricing-plans/subscriptions/me` |
| Subscribe gói | `POST /pricing-plans/subscriptions/me/subscribe/{plan_id}` |
| Check project limit | `GET /pricing-plans/check-project-limit` |
| Check AI limit | `GET /pricing-plans/check-ai-limit` |

Route subscription:

```text
backend/app/api/route/user_subscriptions.py
```

Các endpoint quan trọng:

| Chức năng | Endpoint |
|---|---|
| Subscribe | `POST /user-subscriptions/subscribe` |
| Check subscription | `GET /user-subscriptions/check` |
| Cancel subscription | `POST /user-subscriptions/cancel` |
| Current plan | `GET /user-subscriptions/current-plan` |

## 16. Service subscription khác gì AITransactionService

Có hai lớp kiểm tra liên quan:

### 16.1. `UserSubscriptionService.check_subscription`

File:

```text
backend/app/services/user_subscriptions.py
```

Vai trò:

- Kiểm tra user có subscription active.
- Kiểm tra plan hợp lệ.
- Tính token đã dùng trong tháng.
- Trả `remaining_tokens`.
- Một số service như `CodeSubmissionService.submit_code` gọi hàm này trước khi làm việc.

### 16.2. `AITransactionService._check_plan_limit`

Vai trò:

- Kiểm tra ngay trước lúc gọi AI.
- Nếu vượt `ai_usage_limit` thì chặn.
- Đảm bảo mọi lời gọi AI qua `AITransactionService.chat` đều được kiểm soát.

Điểm phản biện:

> `UserSubscriptionService` kiểm tra quyền dùng hệ thống/tính năng, còn `AITransactionService` kiểm tra trực tiếp trước mỗi lần gọi AI và ghi usage log.

## 17. Project limit có liên quan không

Project limit không quyết định AI provider, nhưng nằm trong logic gói.

File:

```text
backend/app/services/Pricing_plans.py
backend/app/services/projects.py
```

Logic:

```text
plan.max_project
  -> đếm số project của user
  -> nếu đã đạt limit thì chặn tạo project
```

Điểm này dùng để phân biệt:

- `ai_usage_limit`: giới hạn token AI.
- `max_project`: giới hạn số project.
- Provider Groq/Premium: phụ thuộc tên plan/giá plan và API key premium.

## 18. Trường hợp cần chú ý

| Trường hợp | Hành vi hiện tại |
|---|---|
| User không có active subscription | Bị chặn 403 |
| Free hết token | Bị chặn 403 |
| Plus hết token nếu có limit | Bị chặn 403 |
| Plus thiếu `PREMIUM_AI_API_KEY` | Fallback về Groq |
| Groq thiếu `GROQ_API_KEY` | Bị chặn 400 |
| Provider rate limit | Bị chặn 429 |
| Provider lỗi server/API | Trả 502 |
| `tokens_used` provider trả null | Log `tokens_used=None`, lần count sau có thể không tăng đúng |

## 19. Cách trả lời khi phản biện

**Free dùng model nào?**

Free dùng Groq với model cấu hình trong `GROQ_MODEL`, hiện tại là `llama-3.1-8b-instant`.

**Plus dùng model nào?**

Plus dùng premium provider nếu có `PREMIUM_AI_API_KEY`. Cấu hình hiện tại là provider `cerebras`, model `gpt-oss-120b`.

**Nếu Plus không có key premium thì sao?**

Code fallback về Groq.

**Ai là nơi quyết định chọn provider?**

`AITransactionService._get_provider_config(plan)`.

**Ai gọi API thật?**

`AIProviderService.chat` trong `ai_provider_client.py`.

**AI usage được lưu ở đâu?**

Bảng `ai_usage_log` thông qua `AITransactionService._save_ai_usage_log`.

**Giới hạn token tính thế nào?**

Tính tổng `AIUsageLogs.tokens_used` của user từ đầu tháng đến hiện tại, so với `PricingPlans.ai_usage_limit`.

**Muốn chỉnh model thì sửa ở đâu?**

Sửa trong config/env:

```text
GROQ_MODEL
PREMIUM_AI_MODEL
GROQ_BASE_URL
PREMIUM_AI_BASE_URL
```

## 20. Kết luận ngắn

Luồng điều phối AI hiện tại là:

```text
Service nghiệp vụ
  -> AITransactionService.chat
  -> lấy plan hiện tại
  -> kiểm tra ai_usage_limit
  -> chọn Groq hoặc premium
  -> AIProviderService.chat gọi API thật
  -> lưu AIUsageLogs
```

Đây là điểm tốt vì logic chọn AI nằm tập trung, không bị rải trong từng chức năng sinh quiz, sinh curriculum hoặc chấm code.
