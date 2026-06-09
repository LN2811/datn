# Workflow: Nộp link GitHub và AI chấm điểm code

## 1. Mục tiêu chức năng

Chức năng này cho phép học viên nộp bài lập trình bằng link GitHub. Hệ thống nhận link repository, tạo bản ghi nộp bài, đọc source code từ GitHub, gửi nội dung phù hợp sang AI để review, sau đó lưu điểm và feedback vào database để frontend hiển thị.

Điểm quan trọng:

- Người dùng không upload file code trực tiếp lên database.
- Backend không lưu toàn bộ source code vào database.
- Backend chỉ tải repo về vùng xử lý tạm, lọc file code cần thiết, ghép nội dung gửi AI, rồi lưu metadata submission và feedback AI.
- Kết quả cuối cùng gồm trạng thái chấm, điểm tổng, 3 điểm thành phần và các phần nhận xét bằng tiếng Việt.

## 2. Actor và màn hình liên quan

Actor chính:

- Học viên: nộp link GitHub, xem điểm, xem feedback, bấm chấm lại.
- Hệ thống backend: xác thực user, lưu submission, đọc repo GitHub, gọi AI, lưu kết quả.
- AI provider: phân tích source code và trả feedback dạng JSON.

Frontend liên quan:

| File | Vai trò |
|---|---|
| `frontend/src/components/home/project.tsx` | Hiển thị project và nút đi tới màn hình nộp/chấm GitHub |
| `frontend/src/components/home/code_review.tsx` | Màn hình Code Review, tải lịch sử nộp bài, hiển thị điểm và feedback |
| `frontend/src/components/home/githubmodal.tsx` | Modal nhập GitHub URL và commit/ref tùy chọn |
| `frontend/src/components/home/lession.css` | Style cho modal, màn hình review và lịch sử |

Backend liên quan:

| File | Vai trò |
|---|---|
| `backend/app/api/route/code_submissions.py` | Khai báo endpoint nộp bài, lịch sử, chi tiết, chấm lại |
| `backend/app/services/code_submissions.py` | Xử lý nghiệp vụ submission và AI grading |
| `backend/app/services/github_code_reader.py` | Đọc repository GitHub và lọc source code |
| `backend/app/services/Ai_code_feedback.py` | Lưu feedback AI và cập nhật điểm/trạng thái submission |
| `backend/app/models/models.py` | Model `CodeSubmissions` và `AICodeFeedback` |

## 3. Luồng tổng quát

```text
Học viên mở project
  -> Bấm nút GitHub/Code Review
  -> Frontend mở màn hình Code Review theo lesson/assignment
  -> Học viên nhập GitHub repository URL
  -> Frontend gọi POST /code-submissions
  -> Backend xác thực user
  -> Backend kiểm tra subscription và assignment
  -> Backend tạo CodeSubmissions với status = "submitted"
  -> Backend chuyển status = "grading"
  -> Backend đọc source code từ GitHub
  -> Backend build prompt chấm code
  -> Backend gọi AI với action_type = "code_review"
  -> Backend parse JSON feedback từ AI
  -> Backend lưu AICodeFeedback
  -> Backend tính điểm tổng và update CodeSubmissions
  -> Frontend tải lại lịch sử và chi tiết submission
  -> UI hiển thị status = "Đã chấm", score và feedback
```

Nếu lỗi xảy ra ở bước đọc GitHub hoặc gọi AI:

```text
submitted -> grading -> failed
```

## 4. Endpoint sử dụng

Prefix router:

```text
/code-submissions
```

| Chức năng | Method | Endpoint | Service |
|---|---:|---|---|
| Nộp link GitHub | POST | `/code-submissions` | `CodeSubmissionService.submit_code` |
| Lấy điểm cao nhất | GET | `/code-submissions/best-score/{assignment_id}` | `CodeSubmissionService.get_best_score` |
| Lấy lịch sử nộp bài | GET | `/code-submissions/history/{assignment_id}` | `CodeSubmissionService.get_submission_history` |
| Lấy chi tiết một lần nộp | GET | `/code-submissions/{submission_id}` | `CodeSubmissionService.get_submission_detail` |
| Chấm lại | POST | `/code-submissions/{submission_id}/retry` | `CodeSubmissionService.retry_ai_grading` |

Các endpoint đều dùng `Authen.get_current_user` để xác định user hiện tại.

## 5. Request nộp GitHub

Frontend gọi:

```http
POST /code-submissions
```

Body:

```json
{
  "assignment_id": "uuid-cua-assignment",
  "github_repo_url": "https://github.com/owner/repository",
  "file_path": null,
  "commit_hash": "main"
}
```

Ý nghĩa:

| Field | Ý nghĩa |
|---|---|
| `assignment_id` | ID bài tập cần nộp |
| `github_repo_url` | Link repository GitHub |
| `file_path` | Dự phòng cho luồng nộp file, hiện luồng AI tập trung vào GitHub URL |
| `commit_hash` | Branch, tag hoặc commit hash muốn chấm; nếu bỏ trống backend dùng default branch |

Validate phía frontend trong `githubmodal.tsx`:

- Không có `assignmentId` thì báo lỗi.
- GitHub URL không được rỗng.
- GitHub URL phải đúng dạng `https://github.com/owner/repo`.
- `commit_hash` là tùy chọn.

Validate phía backend trong `submit_code`:

- User phải có subscription hợp lệ.
- Assignment phải tồn tại.
- Assignment không được inactive.
- Phải có `github_repo_url` hoặc `file_path`.

## 6. Tạo submission

Service:

```text
backend/app/services/code_submissions.py
```

Hàm:

```python
CodeSubmissionService.submit_code(...)
```

Luồng xử lý:

1. Kiểm tra subscription:

```python
self.subscription_service.check_subscription(user_id=user_id)
```

2. Lấy assignment:

```python
assignment = self.session.get(Assignments, assignment_id)
```

3. Tạo bản ghi submission:

```python
submission = CodeSubmissions(
    assignment_id=assignment_id,
    user_id=user_id,
    github_repo_url=github_repo_url or "",
    submitted_at=datetime.utcnow(),
)
```

4. Gán thêm metadata:

```text
file_path
commit_hash
status = "submitted"
```

5. Commit database.

6. Nếu có `github_repo_url`, gọi:

```python
self._trigger_ai_grading(submission.id)
```

Hiện tại quá trình chấm AI chạy đồng bộ trong request nộp bài. Vì vậy nếu repo lớn hoặc AI phản hồi chậm, request `POST /code-submissions` có thể mất vài giây.

## 7. Trạng thái submission

| Status | Ý nghĩa | Khi nào xuất hiện |
|---|---|---|
| `submitted` | Đã tạo bản ghi nộp bài | Sau khi lưu submission |
| `grading` | Đang chấm | Khi backend bắt đầu đọc GitHub và gọi AI |
| `graded` | Đã chấm | Sau khi feedback và điểm đã được lưu |
| `failed` | Chấm lỗi | Khi đọc GitHub, parse hoặc gọi AI thất bại |

Quy tắc hiển thị frontend:

- Nếu submission có `feedback` hoặc có `score`, UI hiển thị `Đã chấm`.
- Nếu chưa có feedback và status là `grading`, UI hiển thị `Đang chấm`.
- Nếu chưa có feedback và chưa có score, UI hiển thị `Chưa chấm` hoặc trạng thái tương ứng.

## 8. Đọc source code từ GitHub

Service:

```text
backend/app/services/github_code_reader.py
```

Hàm entry:

```python
GithubCodeReader.read_code_repo(github_repo_url, ref=None)
```

Luồng:

1. Parse GitHub URL để lấy `owner` và `repo_name`.
2. Gọi GitHub API lấy metadata repository.
3. Xác định branch/ref cần đọc.
4. Lấy commit hash mới nhất của ref.
5. Tải zipball repository từ GitHub API.
6. Extract an toàn vào thư mục tạm.
7. Lọc các file code hợp lệ.
8. Ghép nội dung file thành `combined_content`.
9. Trả về `GithubCodeSnapshot`.

Kết quả snapshot gồm:

```python
GithubCodeSnapshot(
    repo_url=...,
    owner=...,
    repo_name=...,
    branch=...,
    commit_hash=...,
    files=...,
    combined_content=...,
)
```

## 9. Giới hạn bảo vệ khi đọc repo

Backend không gửi toàn bộ repo sang AI. Nó giới hạn số lượng file, dung lượng file, tổng số ký tự và loại file được phép đọc.

Các giới hạn chính:

```text
MAX_FILES = 40
MAX_FILE_BYTES = 200_000
MAX_TOTAL_CHARS = 60_000
MAX_ZIP_BYTES = 25_000_000
MAX_EXTRACTED_BYTES = 50_000_000
```

Các thư mục thường bị bỏ qua:

```text
.git, .github, node_modules, vendor, __pycache__, dist, build,
target, .next, .venv, venv, .idea, .vscode
```

Các extension code được đọc:

```text
.py, .js, .java, .cpp, .c, .cs, .go, .rb, .php,
.ts, .tsx, .jsx, .html, .css, .json, .xml,
.yaml, .yml, .sh, .bat, .ps1
```

## 10. Repo public và private

Repo public:

- Backend có thể đọc trực tiếp qua GitHub API.

Repo private:

- Backend cần biến môi trường:

```text
GITHUB_TOKEN
```

- Nếu có token, backend gửi header:

```python
headers["Authorization"] = f"token {github_token}"
```

Lưu ý nghiệp vụ:

- Flow hiện tại không lưu GitHub token riêng theo từng user.
- Nếu dùng repo private, token đặt ở server phải có quyền đọc repo đó.

## 11. Gọi AI chấm code

Hàm bắt đầu chấm:

```python
CodeSubmissionService._trigger_ai_grading(submission_id)
```

Luồng chính:

```text
_trigger_ai_grading
  -> lấy CodeSubmissions
  -> lấy Assignments
  -> nếu đã có feedback và không force thì sync score/status rồi return
  -> nếu force thì xóa feedback cũ và reset submission
  -> chuyển status = "grading"
  -> GithubCodeReader.read_code_repo(...)
  -> cập nhật commit_hash thực tế
  -> ContextSelector.select(CODE_REVIEW, ...)
  -> _build_code_review_prompt(...)
  -> AITransactionService.chat(...)
  -> _parse_github_response(...)
  -> _normalize_score_fields(...)
  -> AICodeFeedbackService.create(...)
```

AI được gọi với:

```python
AITransactionService.chat(
    action_type="code_review",
    response_format={"type": "json_object"},
    temperature=0.2,
    max_completion_tokens=1200,
)
```

Ý nghĩa:

- `action_type="code_review"` để ghi log usage riêng cho chức năng chấm code.
- `response_format={"type": "json_object"}` yêu cầu AI trả JSON.
- `temperature=0.2` giúp feedback ổn định hơn.
- `ContextSelector` đưa thêm context liên quan đến project, assignment, rubric hoặc expected outcomes nếu có.

## 12. Prompt yêu cầu AI trả gì

AI được yêu cầu trả đúng một JSON object:

```json
{
  "overview": "Nhận xét tổng quan về chất lượng code",
  "flow_analysis": "Phân tích luồng xử lý chính của code",
  "code_quality_score": 8.5,
  "logic_score": 8.0,
  "performance_score": 7.5,
  "strengths": "Những điểm mạnh của code",
  "weaknesses": "Những điểm yếu của code",
  "improvement_suggestions": "Các gợi ý cải thiện cụ thể",
  "overall_score": 8.0
}
```

Các trường text phải là tiếng Việt có dấu, trừ tên hàm, tên biến, thư viện, framework hoặc thuật ngữ kỹ thuật cần giữ nguyên.

## 13. Parse response AI

Backend parse AI response bằng:

```python
CodeSubmissionService._parse_github_response(content)
```

Xử lý:

- Nếu AI trả JSON hợp lệ, backend lấy các field trong JSON.
- Nếu AI bọc JSON trong markdown hoặc text thừa, backend tách phần từ `{` đến `}`.
- Nếu AI không trả JSON hợp lệ, backend fallback:
  - Lưu nội dung AI vào `overview`.
  - Các điểm thành phần để `None`.
  - Gợi ý người dùng kiểm tra lại source/prompt.

Sau đó backend chuẩn hóa điểm:

```python
CodeSubmissionService._normalize_score_fields(payload)
```

Nếu một trong ba điểm thành phần bị thiếu nhưng có `overall_score`, backend dùng `overall_score` để bù.

## 14. Lưu feedback và tính điểm

Service:

```text
backend/app/services/Ai_code_feedback.py
```

Hàm:

```python
AICodeFeedbackService.create(...)
```

Feedback được lưu vào bảng `ai_code_feedback`.

Các field chính:

| Field | Ý nghĩa |
|---|---|
| `submission_id` | Liên kết tới lần nộp |
| `overview` | Tổng quan |
| `flow_analysis` | Phân tích luồng |
| `code_quality_score` | Điểm chất lượng code |
| `logic_score` | Điểm logic |
| `performance_score` | Điểm hiệu năng |
| `strengths` | Điểm mạnh |
| `weaknesses` | Điểm yếu |
| `improvement_suggestions` | Gợi ý cải thiện |
| `generated_by` | Nguồn tạo feedback, mặc định `ai` |
| `created_at` | Thời điểm tạo |

Điểm tổng được tính bằng trung bình các điểm thành phần có dữ liệu:

```text
total_score = average(code_quality_score, logic_score, performance_score)
```

Sau khi lưu feedback, backend cập nhật bảng `code_submissions`:

```text
status = "graded"
score = total_score
graded_at = datetime.utcnow()
```

Nếu feedback cũ bị lưu dưới dạng JSON string trong `overview`, service có hàm normalize để tách lại thành các field thật trước khi trả về hoặc sync điểm.

## 15. Response trả về frontend

Lịch sử nộp bài:

```http
GET /code-submissions/history/{assignment_id}
```

Chi tiết một lần nộp:

```http
GET /code-submissions/{submission_id}
```

Response mong muốn cho mỗi submission:

```json
{
  "id": "submission-id",
  "assignment_id": "assignment-id",
  "user_id": "user-id",
  "github_repo_url": "https://github.com/owner/repository",
  "file_path": null,
  "commit_hash": "abc123",
  "score": 6.7,
  "status": "graded",
  "submitted_at": "2026-06-03T02:14:00",
  "graded_at": "2026-06-03T02:15:00",
  "feedback": {
    "id": "feedback-id",
    "submission_id": "submission-id",
    "overview": "Bài làm triển khai đúng ý tưởng chính...",
    "flow_analysis": "Luồng xử lý bắt đầu từ...",
    "code_quality_score": 6.5,
    "logic_score": 7.5,
    "performance_score": 6.0,
    "strengths": "Có tương tác rõ ràng, xử lý canvas...",
    "weaknesses": "Cấu trúc file còn rời rạc...",
    "improvement_suggestions": "Nên tách module, xử lý lỗi DOM...",
    "generated_by": "ai",
    "created_at": "2026-06-03T02:15:00"
  }
}
```

Frontend đọc dữ liệu từ:

```ts
selectedSubmission?.feedback ?? latestSubmission?.feedback
```

Sau đó normalize để hỗ trợ cả hai dạng:

- `feedback` là object JSON thật.
- `feedback` là JSON string do dữ liệu cũ/backend cũ trả về.

## 16. Hiển thị trên frontend

Màn hình:

```text
frontend/src/components/home/code_review.tsx
```

Các phần hiển thị:

| UI | Field |
|---|---|
| Tổng quan | `feedback.overview` |
| Phân tích luồng | `feedback.flow_analysis` |
| Chất lượng code | `feedback.code_quality_score` |
| Logic | `feedback.logic_score` |
| Hiệu năng | `feedback.performance_score` |
| Điểm mạnh | `feedback.strengths` |
| Điểm yếu | `feedback.weaknesses` |
| Gợi ý cải thiện | `feedback.improvement_suggestions` |

Điểm hiện tại trên UI:

```ts
totalScore =
  (
    code_quality_score +
    logic_score +
    performance_score
  ) / 3
```

Nếu chưa có feedback, UI hiển thị:

```text
Feedback AI chưa sẵn sàng
```

Nếu có feedback hoặc score, UI hiển thị:

```text
Đã chấm
```

## 17. Chấm lại

Frontend gọi:

```http
POST /code-submissions/{submission_id}/retry
```

Backend:

```python
CodeSubmissionService.retry_ai_grading(...)
```

Luồng:

1. Kiểm tra submission tồn tại.
2. Kiểm tra quyền: user sở hữu submission hoặc là superuser.
3. Gọi `_trigger_ai_grading(force=True)`.
4. Nếu có feedback cũ, xóa feedback cũ.
5. Reset:

```text
score = null
graded_at = null
status = "submitted"
```

6. Đọc lại GitHub, gọi AI lại và lưu feedback mới.
7. Trả chi tiết submission mới cho frontend.

## 18. Vì sao `track_usage=False` khi lưu feedback

Trong `_trigger_ai_grading`, backend đã gọi:

```python
AITransactionService.chat(...)
```

Hàm này đã ghi usage log cho AI. Vì vậy khi lưu feedback:

```python
AICodeFeedbackService.create(..., track_usage=False)
```

mục đích là tránh tính/log usage hai lần cho cùng một lần chấm.

## 19. Các lỗi thường gặp

| Tình huống | Nơi phát hiện | Kết quả |
|---|---|---|
| User chưa đăng nhập | `Authen.get_current_user` | 401/403 |
| User không có subscription | `UserSubscriptionService.check_subscription` | 403 |
| Assignment không tồn tại | `submit_code` | 404 |
| Assignment inactive | `submit_code` | 400 |
| Không gửi GitHub URL hoặc file path | `submit_code` | 400 |
| Link không phải GitHub | `GithubCodeReader._parse_github_url` | 400 |
| Repo không tồn tại/private không có quyền | GitHub API | 404/403 |
| Repo quá lớn | `GithubCodeReader` | 413 |
| Không có file code hợp lệ | `GithubCodeReader.read_code_repo` | 400 |
| AI lỗi hoặc hết quota | `AITransactionService.chat` | 429/502/500 |
| AI trả JSON lỗi | `_parse_github_response` | Fallback text hoặc failed tùy lỗi |

## 20. Checklist demo chức năng

1. Mở project có bài học/assignment.
2. Bấm nút GitHub/Code Review.
3. Nhập link repo public hợp lệ.
4. Bấm nộp bài.
5. Sau khi backend xử lý xong, lịch sử nộp bài có bản ghi mới.
6. Trạng thái chuyển sang `Đã chấm`.
7. Điểm hiện tại không còn là `-`.
8. UI hiển thị đủ:
   - Tổng quan
   - Phân tích luồng
   - Chất lượng code
   - Logic
   - Hiệu năng
   - Điểm mạnh
   - Điểm yếu
   - Gợi ý cải thiện
9. Bấm từng item trong lịch sử, feedback đổi đúng theo lần nộp.
10. Bấm `Chấm lại`, hệ thống tạo feedback mới và không hiển thị JSON thô.

## 21. Câu trả lời nhanh khi phản biện

**Hệ thống chấm code bằng cách nào?**

Học viên nộp link GitHub. Backend đọc source code từ repo, lọc file code cần thiết, gửi sang AI và lưu điểm/feedback vào database.

**Có lưu source code vào database không?**

Không. Database chỉ lưu metadata submission, điểm và feedback AI.

**Điểm tổng tính thế nào?**

Điểm tổng là trung bình của `code_quality_score`, `logic_score` và `performance_score`.

**Vì sao feedback có tiếng Việt?**

Prompt hệ thống yêu cầu AI viết toàn bộ nhận xét bằng tiếng Việt có dấu. Frontend chỉ render các field đã parse, không render raw JSON.

**Repo private có dùng được không?**

Có thể dùng nếu server có `GITHUB_TOKEN` đủ quyền đọc repo. Flow hiện tại chưa hỗ trợ token GitHub riêng cho từng user.

**Chấm lại có tạo submission mới không?**

Không. Chấm lại dùng cùng submission, xóa feedback cũ, reset trạng thái rồi gọi AI để tạo feedback mới.
