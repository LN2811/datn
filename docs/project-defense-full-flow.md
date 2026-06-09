# Bản nắm bắt toàn bộ dự án để phản biện

Tài liệu này giải thích dự án theo hướng **luồng chức năng thực tế**: người dùng bấm gì, API nào nhận, route gọi service nào, service đọc/ghi bảng nào, hàm nào xử lý file, hàm nào chia nhỏ tài liệu, hàm nào gọi AI, và dữ liệu quay lại frontend như thế nào.

Các đường dẫn code chính:

- API route: `backend/app/api/route/`
- Service nghiệp vụ: `backend/app/services/`
- Model DB: `backend/app/models/models.py`
- Cấu hình: `backend/app/core/config.py`
- Kết nối DB sync: `backend/app/core/db.py`
- Kết nối DB async trong `app.main`: `backend/app/database.py`
- File upload lưu vật lý: `backend/app/storage/`

## 1. Kiến trúc tổng thể

Luồng chung của backend:

```text
Frontend
  -> FastAPI route
  -> Authen.get_current_user nếu endpoint cần đăng nhập
  -> Service nghiệp vụ
  -> Database qua SQLModel Session
  -> Service phụ nếu cần: parser, storage, AI, GitHub, MoMo
  -> Trả JSON/model về frontend
```

Ví dụ luồng upload tài liệu:

```text
POST /learning-materials/project/{project_id}/materials
  -> route LearningMaterials.create_material
  -> LearningMaterialService.create_material
  -> storage.save_uploaded_file
  -> tạo LearningMaterials trong DB
  -> MaterialChunkService.save_material_chunk
  -> file_parser.extract_text
  -> ai_service.clean_learning_material_text
  -> ai_service._split_passages
  -> tạo MaterialChunk trong DB
```

Ví dụ luồng sinh bài học:

```text
POST /curriculums/projects/{project_id}/generate-lessons
  -> route curriculum.generate_lessons_for_project
  -> ai_usage_tracking_context
  -> CurriculumService.generate_lessons_for_project
  -> CurriculumGenerationService.generate_from_curriculum
  -> _collect_project_material_text
  -> extract_curriculum_outline_from_toc hoặc generate_curriculum_outline_fallback
  -> tạo Curriculums + CurriculumModules
  -> _ensure_preview_modules_ready
  -> _generate_module_content
  -> generate_lesson_content_from_source
  -> _ensure_question_set_for_modules
  -> QuestionService._create_source_questions
  -> AITransactionService.chat hoặc ai_service.call_llm
```

## 2. Bảng endpoint chính và service tương ứng

| Chức năng | Endpoint chính | Route function | Service chính |
|---|---|---|---|
| Đăng ký | `POST /auth/register` | `login.register` | `UserService.create_user` |
| Đăng nhập | `POST /auth/login` | `login.login` | `LoginService`/auth helper |
| Lấy user hiện tại | `GET /authen/current-user` | `authen.get_current_user` | `Authen.get_current_user` |
| Tạo project | `POST /projects` | `projects.create_project` | `ProjectService.create_project` |
| Dashboard project | `GET /projects/overview` | `projects.get_dashboard_overview` | `ProjectService.get_dashboard_overview` |
| Upload tài liệu | `POST /learning-materials/project/{project_id}/materials` | `LearningMaterials.create_material` | `LearningMaterialService.create_material` |
| Lấy tài liệu project | `GET /learning-materials/project/{project_id}` | `LearningMaterials.get_materials_by_project` | `LearningMaterialService.get_materials_by_project` |
| Sinh curriculum/bài học | `POST /curriculums/projects/{project_id}/generate-lessons` | `curriculum.generate_lessons_for_project` | `CurriculumGenerationService.generate_from_curriculum` |
| Lấy bài học project | `GET /curriculums/projects/{project_id}/lessons` | `curriculum.get_lessons_by_project` | `CurriculumService.get_lessons_by_curriculum` |
| Lấy quiz assignment | `GET /questions/assignment/{assignment_id}/quiz` | `questions.get_assignment_quiz` | `QuestionService.get_assignment_quiz` |
| Nộp quiz assignment | `POST /questions/assignment/{assignment_id}/quiz/submit` | `questions.submit_assignment_quiz` | `QuestionService.submit_assignment_quiz` |
| Lấy quiz module | `GET /questions/modules/{module_id}/quiz` | `questions.get_module_quiz` | `QuestionService.get_module_quiz` |
| Nộp quiz module | `POST /questions/modules/{module_id}/quiz/submit` | `questions.submit_module_quiz` | `QuestionService.submit_module_quiz` |
| Nộp code GitHub | `POST /code-submissions` | `code_submissions.submit_code` | `CodeSubmissionService.submit_code` |
| Xem feedback code | `GET /code-submissions/{submission_id}` | `code_submissions.get_submission_detail` | `CodeSubmissionService.get_submission_detail` |
| Thanh toán MoMo | `POST /payments/momo/create` | `payments.create_momo_payment` | `MomoPaymentService.create_payment` |
| IPN MoMo | `POST /payments/momo/ipn` | `payments.momo_ipn` | `MomoPaymentService.handle_ipn` |
| Danh sách gói | `GET /pricing-plans` | `Pricing_plans.get_pricing_plans` | `PricingPlanService.get_pricing_plans` |
| Subscribe gói | `POST /pricing-plans/subscriptions/me/subscribe/{plan_id}` | `Pricing_plans.subscribe_my_plan` | `PricingPlanService.subscribe_plan` |

## 3. Các bảng DB quan trọng

Các model nằm ở `backend/app/models/models.py`.

| Bảng/model | Mục đích |
|---|---|
| `Users` | Tài khoản người dùng, thông tin profile, quyền admin |
| `Projects` | Dự án học tập của user |
| `LearningMaterials` | Metadata tài liệu upload/link: title, file_path, external_link, uploaded_by |
| `MaterialChunk` | Các đoạn nhỏ đã tách từ tài liệu |
| `Curriculums` | Bộ curriculum được tạo từ tài liệu |
| `CurriculumModules` | Các bài học/module trong curriculum |
| `Assignments` | Bài tập hoặc nhóm câu hỏi/quiz |
| `Questions` | Câu hỏi quiz |
| `QuestionOptions` | Đáp án trắc nghiệm |
| `AssessmentAttempt` | Lần làm bài/quiz |
| `Answers` | Câu trả lời của user |
| `AssessmentResults` | Kết quả đánh giá sau khi submit quiz |
| `AIAnalysis` | Phân tích AI dựa trên assessment result |
| `AIUsageLogs` | Log token/model/action mỗi lần dùng AI |
| `PricingPlans` | Gói Free/Plus/... |
| `UserSubscriptions` | Gói hiện tại của user |
| `CodeSubmissions` | Lần nộp code GitHub |
| `AICodeFeedback` | Feedback AI cho bài code |
| `PaymentTransactions` | Giao dịch MoMo/card |

## 4. Luồng xác thực người dùng

### 4.1. Đăng ký

```text
POST /auth/register
  -> route login.register
  -> UserService.create_user
  -> get_password_hash
  -> lưu Users
```

Hàm chính:

- `UserService.create_user(session, user_in)`:
  - Kiểm tra email có tồn tại không.
  - Kiểm tra email đã bị trùng chưa.
  - Kiểm tra password.
  - Hash password bằng `get_password_hash`.
  - Tạo bản ghi `Users`.

### 4.2. Đăng nhập và user hiện tại

Route đăng nhập set token vào cookie. Các endpoint bảo vệ user dùng:

```text
Depends(Authen.get_current_user)
```

`Authen.get_current_user` sẽ:

1. Đọc cookie `token`.
2. Decode JWT bằng `decode_token`.
3. Lấy `sub` là user id.
4. Query bảng `Users`.
5. Không có token/user thì trả 401.

## 5. Luồng project

### 5.1. Tạo project

```text
POST /projects
  -> route projects.create_project
  -> ProjectService.create_project
  -> ProjectService.project_limit
  -> tạo Projects
```

Hàm quan trọng:

- `ProjectService.create_project(session, project_data, user_id)`:
  - Lấy `owner_id` từ user đăng nhập.
  - Gọi `project_limit` để kiểm tra gói hiện tại cho phép tạo thêm project không.
  - Tạo `Projects(name, description, owner_id)`.

- `ProjectService.project_limit(session, user_id)`:
  - Gọi `_get_current_plan`.
  - Đọc `max_project` của plan.
  - Đếm số project user đang sở hữu.
  - Nếu vượt limit thì trả 403.

### 5.2. Dashboard project

```text
GET /projects/overview
  -> ProjectService.get_dashboard_overview
  -> đọc Projects, Assignments, CodeSubmissions, AssessmentAttempt,
     LearningMaterials, AssessmentResults, AIAnalysis
  -> tổng hợp progress và next_action
```

Hàm `get_dashboard_overview` không chỉ lấy project sở hữu, mà còn lấy project user từng tham gia qua:

- Assessment attempt.
- Assessment result.
- Code submission.

Nó tính:

- Tổng số project.
- Tổng assignment.
- Assignment đã nộp.
- Tiến độ phần trăm.
- Assessment mới nhất.
- Gợi ý hành động tiếp theo.

## 6. Luồng upload tài liệu học tập chi tiết

Đây là phần thường bị hỏi khi phản biện.

### 6.1. API nhận file

Endpoint:

```text
POST /learning-materials/project/{project_id}/materials
```

Route:

```python
backend/app/api/route/LearningMaterials.py
create_material(...)
```

Input dạng form:

- `title`: tên tài liệu.
- `external_link`: link tài liệu ngoài, optional.
- `file_path`: file upload, optional.
- `current_user`: lấy qua `Authen.get_current_user`.

Route gọi:

```python
LearningMaterialService(session).create_material(
    project_id=project_id,
    title=title,
    external_link=external_link,
    file_path=file_path,
    current_user=current_user,
)
```

### 6.2. Service tạo tài liệu

File:

```text
backend/app/services/LearningMaterials.py
```

Hàm:

```python
LearningMaterialService.create_material(...)
```

Luồng xử lý:

1. Query `Projects` theo `project_id`.
2. Không có project thì trả 404.
3. Kiểm tra người dùng chỉ được truyền **một trong hai**:
   - file upload
   - external link
4. Nếu vừa có file vừa có link thì trả 400.
5. Nếu không có cả hai thì trả 400.
6. Nếu có file thì gọi `save_uploaded_file(file_path)`.
7. Tạo bản ghi `LearningMaterials`.
8. Commit DB.
9. Gọi `MaterialChunkService.save_material_chunk(material_id=material.id)`.

### 6.3. File được lưu ở đâu và lưu như thế nào

File:

```text
backend/app/services/storage.py
```

Hàm:

```python
save_uploaded_file(upload_file)
```

Biến:

```python
upload_dir = Path(__file__).resolve().parents[1] / "storage"
```

Nghĩa là file được lưu vào:

```text
backend/app/storage/
```

Các extension được chấp nhận:

```python
allowed_extensions = {".pdf", ".docx", ".pptx", ".txt", ".jpg", ".jpeg", ".png"}
```

Cách đặt tên file:

```python
filename = f"{uuid.uuid4()}{ext}"
```

Ví dụ user upload `tailieu.pdf`, backend không lưu tên gốc mà lưu dạng:

```text
backend/app/storage/2d6a2f4f-...-....pdf
```

Lý do:

- Tránh trùng tên file.
- Tránh user kiểm soát tên file trên server.
- Dễ lưu metadata trong DB.

Hàm trả về:

```python
{
    "file_path": "đường_dẫn_file_đã_lưu",
    "filename": "tên_uuid.pdf"
}
```

### 6.4. Metadata tài liệu được lưu vào DB như thế nào

Sau khi lưu file, `LearningMaterialService.create_material` tạo:

```python
LearningMaterials(
    project_id=project_id,
    title=title,
    file_path=saved_file_path,
    external_link=external_link,
    uploaded_by=current_user.id,
)
```

Bảng DB:

```text
learning_materials
```

Các field quan trọng:

- `id`: id tài liệu.
- `project_id`: tài liệu thuộc project nào.
- `uploaded_by`: user upload.
- `title`: tiêu đề tài liệu.
- `file_path`: đường dẫn file vật lý nếu upload file.
- `external_link`: link ngoài nếu dùng link.
- `created_at`: thời điểm tạo.

Điểm quan trọng để nói:

> DB không lưu binary file. DB chỉ lưu đường dẫn file và metadata. File thật nằm trong thư mục storage của backend.

### 6.5. Sau khi lưu DB thì tài liệu được chia nhỏ như thế nào

Sau khi tạo `LearningMaterials`, service gọi:

```python
MaterialChunkService(self.session).save_material_chunk(material_id=material.id)
```

File:

```text
backend/app/services/material_chunk.py
```

Hàm:

```python
MaterialChunkService.save_material_chunk(material_id, text=None)
```

Luồng:

1. Query `LearningMaterials` theo `material_id`.
2. Nếu không có thì 404.
3. Kiểm tra bảng `MaterialChunk` xem material này đã chunk chưa.
4. Nếu đã có chunk thì trả lại chunk cũ, không tạo trùng.
5. Nếu chưa có:
   - lấy source = `material.file_path` hoặc `material.external_link`
   - gọi `extract_text(source)`
6. Text sau extract được đưa qua:
   - `clean_learning_material_text(text)`
   - `_split_passages(text)`
7. Mỗi passage được lưu thành một dòng `MaterialChunk`.

Tạo chunk:

```python
MaterialChunk(
    material_id=material_id,
    content=chunk,
    chunk_index=index,
)
```

Bảng DB:

```text
material_chunks
```

Mỗi chunk có:

- `material_id`: thuộc tài liệu nào.
- `content`: nội dung đoạn.
- `chunk_index`: thứ tự đoạn.

### 6.6. Hàm nào đọc nội dung file

File:

```text
backend/app/services/file_parser.py
```

Hàm entry:

```python
extract_text(path_or_url)
```

Nó tự nhận diện loại nguồn:

| Nguồn | Hàm xử lý |
|---|---|
| Web URL | `_extract_text_from_web` |
| `.txt` | đọc file trực tiếp bằng UTF-8 |
| `.pdf` có text layer | `_extract_text_from_pdf_layer`, `extract_text_pdf` |
| `.pdf` scan | `extract_text_with_ocr` |
| `.docx` | `_extract_zip_xml_text(..., prefixes=("word/",))` |
| `.pptx` | `_extract_zip_xml_text(..., prefixes=("ppt/slides/",))` |
| `.jpg/.jpeg/.png` | `extract_text_with_ocr` |

PDF có nhiều fallback:

```text
PyPDF2 -> pdfplumber -> OCR bằng Tesseract/Poppler
```

Điểm phản biện:

> Hệ thống hỗ trợ cả PDF text thường và PDF scan. Nếu PDF scan thì cần Tesseract và Poppler để OCR.

### 6.7. Hàm nào làm sạch text

Có hai lớp làm sạch:

1. `text_cleaner.clean_vietnamese_text`
2. `ai_service.clean_learning_material_text`

`clean_vietnamese_text` xử lý:

- Unicode normalize.
- Khoảng trắng.
- Lỗi OCR tách âm tiết tiếng Việt.
- Khoảng trắng quanh dấu câu.
- Dòng trống thừa.

`clean_learning_material_text` xử lý thêm:

- Bỏ ký tự control.
- Sửa từ bị xuống dòng do gạch nối.
- Bỏ header/footer lặp.
- Bỏ dòng noise/số trang.
- Chuẩn hóa đoạn văn.

### 6.8. Tài liệu được lấy lại từ DB như thế nào

Các hàm lấy tài liệu:

```python
LearningMaterialService.get_materials_by_project(project_id)
LearningMaterialService.get_material_detail(material_id)
```

Khi cần nội dung để sinh curriculum/câu hỏi, hệ thống không chỉ lấy metadata tài liệu. Nó lấy text bằng một trong hai cách:

1. Từ `MaterialChunk` đã lưu.
2. Hoặc extract lại từ file/link nếu flow đó cần full text.

Ví dụ sinh câu hỏi assignment:

```python
QuestionService._collect_assignment_source_text(...)
  -> lấy assignment.project.materials
  -> query MaterialChunk theo material.id
  -> nối content các chunk
```

Ví dụ sinh curriculum:

```python
CurriculumGenerationService._collect_project_material_text(...)
  -> query LearningMaterials theo project_id
  -> với mỗi material:
       source = material.file_path or material.external_link
       extracted_text = clean_learning_material_text(extract_text(source))
  -> nối thành full_text
```

Điểm cần nói rõ:

> Với câu hỏi, hệ thống ưu tiên dùng chunk đã lưu để tiết kiệm xử lý. Với sinh curriculum, service hiện đang gom full text từ materials để tạo outline và bài học.

## 7. Luồng sinh curriculum/bài học từ tài liệu

### 7.1. Endpoint

```text
POST /curriculums/projects/{project_id}/generate-lessons
```

Route:

```python
backend/app/api/route/curriculum.py
generate_lessons_for_project(...)
```

Route bọc trong:

```python
ai_usage_tracking_context(
    session=session,
    user_id=current_user.id,
    project_id=project_id,
    action_type="generate_curriculum",
)
```

Mục đích: nếu các hàm AI cũ dùng `call_llm`, usage sẽ được log lại.

### 7.2. Service entry

Route gọi:

```python
CurriculumService().generate_lessons_for_project(
    session=session,
    project_id=project_id,
    force_regenerate=force_regenerate,
    user_id=current_user.id,
)
```

Sau đó:

```python
CurriculumGenerationService().generate_from_curriculum(...)
```

### 7.3. Lấy tài liệu để sinh curriculum

Hàm:

```python
CurriculumGenerationService._collect_project_material_text(session, project_id)
```

Luồng:

1. Query `LearningMaterials` theo `project_id`.
2. Với mỗi material:
   - lấy `source = material.file_path or material.external_link`
   - gọi `extract_text(source)`
   - gọi `clean_learning_material_text(...)`
3. Ghép lại thành `full_text`.
4. Nếu không có text thì trả lỗi 400.

### 7.4. Tạo outline curriculum

Trong `generate_from_curriculum`:

```python
outline = extract_curriculum_outline_from_toc(full_text)
```

Nếu có mục lục:

- Parse mục lục.
- Lấy các entry phù hợp làm module.
- `generated_by = "toc"`.

Nếu không có mục lục:

```python
outline = generate_curriculum_outline_fallback(full_text)
```

Fallback sẽ:

- Tìm heading trong tài liệu.
- Nếu có heading thì dùng heading làm module.
- Nếu không có heading rõ ràng thì tạo một module chung từ nội dung tài liệu.
- `generated_by = "source"`.

### 7.5. Lưu curriculum và module

Tạo curriculum:

```python
Curriculums(
    project_id=project_id,
    title=curriculum_title,
    overview=curriculum_overview,
    generated_by=generated_by,
    total_module=len(modules),
    ready_module=0,
)
```

Tạo module:

```python
CurriculumGenerationService._create_pending_modules(...)
```

Mỗi module ban đầu:

```python
CurriculumModules(
    curriculum_id=curriculum.id,
    title=title,
    description=description,
    content=None,
    generate_status="pending",
    is_preview=index <= preview_count,
    order_index=index,
)
```

### 7.6. Generate nội dung bài học

Chỉ generate trước các module preview:

```python
_ensure_preview_modules_ready(...)
```

Với từng module cần generate:

```python
_generate_module_content(...)
```

Hàm này:

1. Set `module.generate_status = "generating"`.
2. Gọi:

```python
generate_lesson_content_from_source(
    text=full_text,
    curriculum_title=curriculum.title,
    overview=curriculum.overview or "",
    module_title=module.title,
    module_description=module.description or "",
)
```

3. Nếu lỗi thì fallback:

```python
generate_lesson_content_fallback(...)
```

4. Làm sạch content bằng `clean_vietnamese_text`.
5. Set:

```python
module.content = ...
module.generate_status = "ready"
curriculum.ready_module += 1
```

### 7.7. Khi người dùng mở bài học

Nếu module chưa ready, frontend/backend có thể gọi:

```python
CurriculumGenerationService.ensure_module_ready(session, module_id)
```

Luồng:

1. Lấy module và curriculum.
2. Nếu module đã `ready` và có content thì trả luôn.
3. Nếu đang `generating` thì trả trạng thái hiện tại.
4. Nếu chưa có content thì gom lại tài liệu project.
5. Gọi `_generate_module_content`.

### 7.8. Prefetch bài tiếp theo

Hàm:

```python
prefetch_next_modules(session, module_id, limit=2)
prefetch_next_modules_background(module_id, limit=2, user_id=None)
```

Mục đích:

- Khi user đang học bài hiện tại, hệ thống có thể chuẩn bị trước bài tiếp theo.
- Tránh chờ lâu khi user chuyển bài.

## 8. Luồng sinh câu hỏi quiz

### 8.1. Lấy quiz theo assignment

Endpoint:

```text
GET /questions/assignment/{assignment_id}/quiz
```

Route:

```python
QuestionService().get_assignment_quiz(
    session=session,
    assignment_id=assignment_id,
    user_id=current_user.id,
)
```

Luồng service:

```text
get_assignment_quiz
  -> _ensure_assignment_questions
  -> nếu chưa có câu hỏi đủ tốt:
       _collect_assignment_source_text
       _create_source_questions
       _generate_question_payloads_from_source
       AITransactionService.chat
       _parse_ai_questions
       _normalize_ai_question_item
       _create_question_record
       _create_option_records
  -> trả questions + options, không trả đáp án đúng
```

### 8.2. Lấy quiz theo module bài học

Endpoint:

```text
GET /questions/modules/{module_id}/quiz
```

Route gọi:

```python
QuestionService().get_module_quiz(...)
```

Luồng:

```text
get_module_quiz
  -> query CurriculumModules
  -> query Curriculums
  -> _ensure_module_questions
  -> _get_or_create_module_assignment
  -> _extract_lesson_source_text(module.content)
  -> _create_source_questions
  -> AITransactionService.chat
  -> lưu Questions + QuestionOptions
```

### 8.3. AI sinh câu hỏi ở đâu

Hàm gọi AI chính:

```python
QuestionService._generate_question_payloads_from_source(...)
```

Nếu có `session`, `user_id`, `project_id`, hàm này gọi:

```python
AITransactionService.chat(
    db=session,
    user_id=user_id,
    project_id=project_id,
    action_type="generate_quiz_questions",
    messages=[{"role": "user", "content": prompt}],
    response_format={"type": "json_object"},
    temperature=0.1,
    max_completion_tokens=QUIZ_COMPLETION_TOKENS,
)
```

Nếu không có session/user/project thì dùng flow cũ:

```python
ai_service.call_llm(...)
```

### 8.4. Prompt sinh câu hỏi

Hàm:

```python
QuestionService._build_source_quiz_prompt(source_text)
```

Prompt yêu cầu:

- Chỉ trả JSON hợp lệ.
- Viết tiếng Việt có dấu.
- Chỉ dùng `SOURCE_TEXT`.
- Tạo tối đa `QUESTIONS_PER_QUIZ` câu.
- Mỗi câu có đúng 4 option.
- Có `correct_index`.
- Có `source_quote` được copy từ tài liệu.

### 8.5. Kiểm soát chất lượng câu hỏi

Sau khi AI trả JSON:

```text
_parse_ai_questions
  -> _normalize_ai_question_item
     -> kiểm tra content có dấu nếu source có dấu
     -> loại câu hỏi generic/template
     -> _normalize_options: đúng 4 option, đúng 1 đáp án đúng
     -> _source_contains_quote: source_quote phải nằm trong tài liệu
```

Điểm phản biện:

> Hệ thống không tin mù quáng response AI. AI trả câu hỏi xong vẫn phải qua các lớp validate trước khi lưu DB.

### 8.6. Số lượng câu hỏi

Hằng số nằm ở:

```text
backend/app/services/quiz_templates.py
QUESTIONS_PER_QUIZ = 10
```

Nếu muốn 20 câu:

```python
QUESTIONS_PER_QUIZ = 20
```

Nên tăng thêm:

```text
backend/app/services/questions.py
QUIZ_COMPLETION_TOKENS = 1800
```

Ví dụ tăng lên `3200` để AI có đủ token trả 20 câu JSON.

## 9. Luồng nộp quiz và tính điểm

### 9.1. Nộp quiz assignment

Endpoint:

```text
POST /questions/assignment/{assignment_id}/quiz/submit
```

Route gọi:

```python
QuestionService().submit_assignment_quiz(...)
```

Luồng:

1. Query assignment.
2. Query toàn bộ questions của assignment.
3. Validate mỗi answer:
   - question có thuộc assignment không.
   - không duplicate question.
   - selected option có thuộc question không.
4. Tạo `AssessmentAttempt`.
5. Với từng câu:
   - tìm option đúng.
   - so sánh option user chọn.
   - tạo `Answers`.
6. Tính:

```python
percentage = round((correct_count / total_questions) * 100, 2)
```

7. Commit DB.
8. Gọi:

```python
_create_quiz_assessment_result(session, attempt_id)
```

### 9.2. Tạo assessment result

Hàm:

```python
AssessmentResultService.create_from_attempt(attempt_id)
```

Luồng:

1. Query attempt.
2. Query answers.
3. Tính điểm trọng số:

```python
_calculate_weighted_score(answers)
```

4. Suy ra readiness:

```python
_calculate_readiness(total_score)
```

Quy tắc:

- `> 80`: high
- `>= 50`: medium
- `< 50`: low

5. Tạo `AssessmentResults`.
6. Cố gắng gọi:

```python
AIAnalysisService.generate(result.id)
```

Nếu AI quota/rate limit lỗi 403/429 thì vẫn giữ result thành công.

### 9.3. AI analysis sau quiz

Hàm:

```python
AIAnalysisService.generate(result_id)
```

Hiện tại phân tích dựa theo rule từ `readiness_level`, chưa gọi LLM thật. Nó tạo:

- `analysis_text`
- `strengths`
- `weaknesses`
- `recommendations`

Sau đó log usage bằng `AIUsageService`.

## 10. Luồng chấm code qua GitHub

### 10.1. Endpoint nộp code

```text
POST /code-submissions
```

Body:

```json
{
  "assignment_id": "...",
  "github_repo_url": "https://github.com/owner/repo",
  "file_path": null,
  "commit_hash": null
}
```

Route:

```python
backend/app/api/route/code_submissions.py
submit_code(...)
```

Gọi service:

```python
CodeSubmissionService(session).submit_code(...)
```

### 10.2. Tạo submission

Hàm:

```python
CodeSubmissionService.submit_code(...)
```

Luồng:

1. Kiểm tra user có subscription:

```python
UserSubscriptionService.check_subscription(user_id)
```

2. Query assignment.
3. Validate phải có `github_repo_url` hoặc `file_path`.
4. Tạo `CodeSubmissions`:

```python
CodeSubmissions(
    assignment_id=assignment_id,
    user_id=user_id,
    github_repo_url=github_repo_url or "",
    submitted_at=datetime.utcnow(),
)
```

5. Set thêm nếu model có:

- `file_path`
- `commit_hash`
- `status = "submitted"`

6. Commit DB.
7. Nếu có GitHub URL thì gọi:

```python
_trigger_ai_grading(submission.id)
```

### 10.3. Đọc repo GitHub

Hàm:

```python
GithubCodeReader.read_code_repo(github_repo_url, ref=None)
```

File:

```text
backend/app/services/github_code_reader.py
```

Luồng:

1. `_parse_github_url`:
   - Chỉ chấp nhận domain `github.com` hoặc `www.github.com`.
   - Parse owner/repo.
   - Validate ký tự owner/repo.
2. `_get_repo_metadata`:
   - Gọi GitHub API `/repos/{owner}/{repo}`.
   - Lấy default branch.
3. `_get_latest_commit_hash`:
   - Lấy commit SHA của branch/ref.
4. `_download_repo_zip`:
   - Tải zipball.
   - Chặn zip quá lớn bằng `MAX_ZIP_BYTES`.
5. `_safe_extract`:
   - Extract vào thư mục tạm.
   - Chặn path traversal.
   - Chặn tổng dung lượng extract quá lớn.
6. `_collect_code_files`:
   - Bỏ qua thư mục như `.git`, `.github`, `node_modules`, `venv`, `dist`, `build`.
   - Chỉ lấy file code theo extension: `.py`, `.js`, `.ts`, `.java`, `.html`, `.css`, `.json`, ...
   - Giới hạn:
     - `MAX_FILES = 40`
     - `MAX_FILE_BYTES = 200_000`
     - `MAX_TOTAL_CHARS = 60_000`
7. `_combine_files`:
   - Ghép các file thành text:

```text
// File: src/main.py
...
// File: tests/test_main.py
...
```

Trả về `GithubCodeSnapshot` gồm:

- repo_url
- owner
- repo_name
- branch/ref
- commit_hash
- files
- combined_content

### 10.4. AI chấm code ở đâu

Hàm:

```python
CodeSubmissionService._trigger_ai_grading(submission_id)
```

Luồng:

```text
_trigger_ai_grading
  -> query CodeSubmissions
  -> query Assignments
  -> nếu đã có AICodeFeedback thì return
  -> status = "grading"
  -> GithubCodeReader.read_code_repo
  -> lưu commit_hash
  -> _build_code_review_prompt
  -> AITransactionService.chat(action_type="code_review")
  -> _parse_github_response
  -> AICodeFeedbackService.create(track_usage=False)
  -> status = "graded", score trung bình
```

Prompt chấm code:

```python
CodeSubmissionService._build_code_review_prompt(...)
```

Prompt yêu cầu AI trả JSON với các key:

- `overview`
- `code_quality_score`
- `logic_score`
- `performance_score`
- `strengths`
- `weaknesses`
- `improvement_suggestions`
- `flow_analysis`
- `overall_score`

### 10.5. Lưu feedback code

Hàm:

```python
AICodeFeedbackService.create(...)
```

Luồng:

1. Query submission.
2. Kiểm tra feedback đã tồn tại chưa.
3. Tạo `AICodeFeedback`.
4. Nếu có đủ 3 điểm:

```python
final_score = (code_quality_score + logic_score + performance_score) / 3
```

5. Cập nhật submission:

- `score = final_score`
- `status = "graded"`
- `graded_at = now`

Lưu ý:

`CodeSubmissionService` gọi `AITransactionService.chat`, mà hàm này đã log usage rồi, nên khi gọi `AICodeFeedbackService.create` truyền `track_usage=False` để tránh log AI hai lần.

### 10.6. Flow tổng hợp từ người dùng đến feedback

Toàn bộ flow nộp bài code bằng link GitHub có thể trình bày như sau:

```text
Người dùng nhập link GitHub
  -> Frontend gọi POST /code-submissions
  -> Backend xác thực JWT bằng Authen.get_current_user
  -> Route code_submissions.submit_code
  -> CodeSubmissionService.submit_code
  -> check subscription
  -> kiểm tra assignment tồn tại và còn active
  -> tạo bản ghi CodeSubmissions status = "submitted"
  -> nếu có github_repo_url thì gọi _trigger_ai_grading
  -> status = "grading"
  -> GithubCodeReader tải repo từ GitHub
  -> lọc file code, giới hạn dung lượng, ghép source code
  -> _build_code_review_prompt
  -> AITransactionService.chat(action_type="code_review")
  -> AI provider trả JSON feedback
  -> _parse_github_response
  -> AICodeFeedbackService.create
  -> tạo AICodeFeedback
  -> tính score trung bình
  -> cập nhật CodeSubmissions status = "graded", score, graded_at
  -> frontend lấy chi tiết bằng GET /code-submissions/{submission_id}
```

Điểm quan trọng:

- Đây là luồng chấm đồng bộ trong request `POST /code-submissions`, không phải background job.
- Nếu GitHub hoặc AI phản hồi chậm thì request nộp bài cũng chậm.
- Nếu xảy ra lỗi khi đọc GitHub hoặc gọi AI, submission được cập nhật `status = "failed"`.
- Nếu chỉ gửi `file_path` mà không gửi `github_repo_url`, backend chỉ tạo submission, hiện tại chưa tự chấm AI.

### 10.7. Các endpoint liên quan đến nộp code

File route chính:

```text
backend/app/api/route/code_submissions.py
```

Các endpoint:

| Chức năng | Method | Endpoint | Hàm route | Hàm service |
|---|---:|---|---|---|
| Nộp bài code | POST | `/code-submissions` | `submit_code` | `CodeSubmissionService.submit_code` |
| Lấy điểm cao nhất | GET | `/code-submissions/best-score/{assignment_id}` | `get_best_score` | `CodeSubmissionService.get_best_score` |
| Lịch sử nộp bài | GET | `/code-submissions/history/{assignment_id}` | `get_submission_history` | `CodeSubmissionService.get_submission_history` |
| Chi tiết bài nộp + feedback | GET | `/code-submissions/{submission_id}` | `get_submission_detail` | `CodeSubmissionService.get_submission_detail` |

File route feedback phụ:

```text
backend/app/api/route/ai_code_feedback.py
```

Các endpoint phụ:

| Chức năng | Method | Endpoint | Service |
|---|---:|---|---|
| Tạo feedback thủ công | POST | `/ai-code-feedback` | `AICodeFeedbackService.create` |
| Lấy feedback theo submission | GET | `/ai-code-feedback/submission/{submission_id}` | `AICodeFeedbackService.get_by_submission` |
| Sửa feedback | PATCH | `/ai-code-feedback/{feedback_id}` | `AICodeFeedbackService.update` |
| Xóa feedback | DELETE | `/ai-code-feedback/{feedback_id}` | `AICodeFeedbackService.delete` |
| Thống kê feedback admin | GET | `/ai-code-feedback/admin/stats` | `AICodeFeedbackService.admin_stats` |

Endpoint được gắn vào app tại:

```python
api_router.include_router(code_submissions.router, prefix="/code-submissions", tags=["code-submissions"])
api_router.include_router(ai_code_feedback.router, prefix="/ai-code-feedback", tags=["ai-code-feedback"])
```

File:

```text
backend/app/api/main.py
```

### 10.8. Request nộp bài GitHub gồm những gì

Body `POST /code-submissions`:

```json
{
  "assignment_id": "uuid của bài tập",
  "github_repo_url": "https://github.com/owner/repo",
  "file_path": null,
  "commit_hash": null
}
```

Ý nghĩa:

- `assignment_id`: bài tập mà người dùng đang nộp.
- `github_repo_url`: link repository GitHub. Đây là dữ liệu chính để hệ thống tải code về chấm.
- `file_path`: có trong schema để hỗ trợ kiểu nộp bằng file/path, nhưng hiện flow AI tự chấm đang xử lý theo GitHub URL.
- `commit_hash`: được truyền vào `GithubCodeReader.read_code_repo(..., ref=commit_hash)`.

Lưu ý về `commit_hash`:

- Nếu người dùng không gửi `commit_hash`, backend dùng default branch của repo.
- Nếu người dùng gửi `commit_hash` hoặc ref, backend dùng nó làm ref để tải zipball.
- Sau khi đọc repo, backend cập nhật lại `submission.commit_hash = code_snapshot.commit_hash`.
- Nếu GitHub API không lấy được SHA của ref thì `commit_hash` có thể là `None`, nhưng repo vẫn có thể được tải nếu zipball tải thành công.

### 10.9. Dữ liệu được lưu ở bảng nào

Model:

```python
class CodeSubmissions(BaseModel, table=True):
    __tablename__ = "code_submissions"
```

File:

```text
backend/app/models/models.py
```

Các cột quan trọng:

| Cột | Ý nghĩa |
|---|---|
| `id` | ID của lần nộp bài |
| `assignment_id` | Bài tập được nộp |
| `user_id` | Người nộp |
| `github_repo_url` | Link GitHub repo |
| `file_path` | Đường dẫn file nếu dùng flow file |
| `commit_hash` | Commit/ref đã chấm |
| `score` | Điểm cuối cùng, tính trung bình từ 3 điểm AI |
| `status` | `submitted`, `grading`, `graded`, `failed` |
| `submitted_at` | Thời điểm nộp |
| `graded_at` | Thời điểm chấm xong |

Feedback AI lưu ở bảng:

```python
class AICodeFeedback(BaseModel, table=True):
    __tablename__ = "ai_code_feedback"
```

Các cột quan trọng:

| Cột | Ý nghĩa |
|---|---|
| `submission_id` | Liên kết về `code_submissions.id` |
| `overview` | Nhận xét tổng quan |
| `flow_analysis` | Phân tích luồng xử lý code |
| `code_quality_score` | Điểm chất lượng code |
| `logic_score` | Điểm logic |
| `performance_score` | Điểm hiệu năng |
| `strengths` | Điểm mạnh |
| `weaknesses` | Điểm yếu |
| `improvement_suggestions` | Gợi ý cải thiện |
| `generated_by` | Nguồn tạo feedback, mặc định `ai` |
| `created_at` | Thời điểm tạo feedback |

Migration thêm các cột chấm code:

```text
backend/app/alembic/versions/20260518_add_code_review_grading_columns.py
```

### 10.10. GithubCodeReader bảo vệ và giới hạn repo như thế nào

File:

```text
backend/app/services/github_code_reader.py
```

Các hằng số giới hạn:

```python
MAX_FILES = 40
MAX_FILE_BYTES = 200_000
MAX_TOTAL_CHARS = 60_000
MAX_ZIP_BYTES = 25_000_000
MAX_EXTRACTED_BYTES = 50_000_000
```

Cơ chế bảo vệ:

- Chỉ chấp nhận link có domain `github.com` hoặc `www.github.com`.
- Bắt buộc URL có dạng owner/repo.
- Validate ký tự `owner` và `repo_name`.
- Gọi GitHub API để lấy metadata repo và default branch.
- Tải zipball từ GitHub thay vì clone git.
- Kiểm tra zip không quá `25MB`.
- Khi extract kiểm tra path traversal, không cho file trong zip thoát khỏi thư mục tạm.
- Chặn tổng dung lượng sau extract quá `50MB`.
- Bỏ qua thư mục nặng hoặc không cần thiết: `.git`, `.github`, `node_modules`, `vendor`, `venv`, `.venv`, `dist`, `build`, `target`, `.next`, `.idea`, `.vscode`.
- Chỉ đọc các extension code được cho phép.
- Mỗi file tối đa `200_000` bytes.
- Tổng source gửi sang AI tối đa khoảng `60_000` ký tự.

Danh sách extension được đọc:

```text
.py, .js, .java, .cpp, .c, .cs, .go, .rb, .php,
.ts, .tsx, .jsx, .html, .css, .json, .xml,
.yaml, .yml, .sh, .bat, .ps1
```

Nếu repo không có file code hợp lệ thì trả lỗi:

```text
400 No code files found in the repository.
```

Nếu repo không tồn tại hoặc repo private mà token không có quyền thì trả lỗi:

```text
404 GitHub repository not found or private.
```

### 10.11. Token GitHub dùng ở đâu

Hàm:

```python
GithubCodeReader._github_headers()
```

Luồng:

1. Tạo header mặc định:

```python
{
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "CodeMasterApp/1.0",
}
```

2. Nếu có biến môi trường:

```text
GITHUB_TOKEN
```

thì thêm:

```python
headers["Authorization"] = f"token {github_token}"
```

Ý nghĩa phản biện:

> Hệ thống đọc repo public được ngay. Nếu cần đọc repo private thì server phải cấu hình `GITHUB_TOKEN` có quyền đọc repo đó. Backend không lưu token của từng người dùng trong DB ở flow hiện tại.

### 10.12. AI chấm bài bằng prompt nào và provider nào

Hàm build prompt:

```python
CodeSubmissionService._build_code_review_prompt(...)
```

Prompt gồm:

- Tiêu đề bài tập.
- Mô tả bài tập.
- URL repository.
- Branch/ref.
- Commit.
- Toàn bộ source code đã được `GithubCodeReader` lọc và ghép lại.

Hàm gọi AI:

```python
AITransactionService.chat(
    db=self.session,
    user_id=submission.user_id,
    project_id=assignment.project_id,
    action_type="code_review",
    messages=[...],
    response_format={"type": "json_object"},
    temperature=0.2,
    max_completion_tokens=1200,
)
```

Điểm cần nhấn mạnh:

- `action_type = "code_review"` nên usage log phân biệt được với sinh bài học hoặc sinh quiz.
- `response_format={"type": "json_object"}` yêu cầu AI trả JSON.
- `temperature=0.2` để kết quả chấm ổn định hơn.
- `max_completion_tokens=1200` lấy từ `CODE_REVIEW_COMPLETION_TOKENS`.
- Provider/model không gọi trực tiếp trong service chấm code. Nó đi qua `AITransactionService`, service này chọn Groq hoặc premium provider theo gói người dùng.

### 10.13. AI trả gì và hệ thống dùng gì

AI được yêu cầu trả đúng một JSON object:

```json
{
  "overview": "Nhận xét tổng quan về chất lượng code",
  "code_quality_score": 8.5,
  "logic_score": 8.0,
  "performance_score": 7.5,
  "strengths": "Những điểm mạnh của code",
  "weaknesses": "Những điểm yếu của code",
  "improvement_suggestions": "Các gợi ý cải thiện cụ thể",
  "flow_analysis": "Phân tích luồng xử lý chính của code",
  "overall_score": 8.0
}
```

Sau khi AI trả về:

1. `_extract_github_info` bỏ markdown code fence nếu AI bọc JSON trong markdown.
2. `_parse_github_response` parse JSON.
3. Nếu JSON lỗi, hệ thống fallback thành feedback text thường.
4. `_to_float_or_none` ép điểm về float và clamp trong khoảng `0` đến `10`.
5. `_string_or_none` ép các field text về string.
6. `AICodeFeedbackService.create` lưu feedback vào DB.

Điểm số cuối cùng:

```python
final_score = (
    code_quality_score +
    logic_score +
    performance_score
) / 3
```

Hiện tại `overall_score` có trong prompt nhưng chưa được lưu trực tiếp và chưa được dùng để tính điểm. Điểm cuối cùng lấy trung bình 3 điểm: chất lượng code, logic, hiệu năng.

### 10.14. Trạng thái của một submission

Các trạng thái chính:

| Status | Khi nào xuất hiện |
|---|---|
| `submitted` | Vừa tạo bản ghi nộp bài |
| `grading` | Bắt đầu tải repo GitHub và gọi AI |
| `graded` | Có feedback và đủ 3 điểm để tính `score` |
| `failed` | Lỗi đọc GitHub, lỗi tải zip, lỗi AI hoặc lỗi xử lý bất ngờ |

Luồng trạng thái bình thường:

```text
submitted -> grading -> graded
```

Luồng lỗi:

```text
submitted -> grading -> failed
```

Điểm cần lưu ý:

- Nếu AI trả JSON hợp lệ nhưng thiếu một trong ba điểm `code_quality_score`, `logic_score`, `performance_score`, feedback vẫn có thể được tạo nhưng `score` và `graded_at` không được cập nhật.
- Trong trường hợp đó status có thể còn ở `grading`. Khi phản biện có thể nói hệ thống đang kỳ vọng AI trả đủ 3 điểm; nếu muốn chắc chắn hơn thì nên thêm fallback cập nhật status ngay cả khi thiếu điểm.
- Nếu submission đã có `AICodeFeedback`, `_trigger_ai_grading` sẽ không chấm lại để tránh tạo feedback trùng.

### 10.15. Frontend hiện đang gọi flow này chưa

Trong frontend hiện có generated SDK:

```ts
submitCodeCodeSubmissionsPost(...)
getBestScoreCodeSubmissionsBestScoreAssignmentIdGet(...)
getSubmissionHistoryCodeSubmissionsHistoryAssignmentIdGet(...)
getSubmissionDetailCodeSubmissionsSubmissionIdGet(...)
```

File:

```text
frontend/src/generated/sdk.gen.ts
frontend/src/generated/types.gen.ts
```

Type request:

```ts
export type SubmissionCreateBody = {
    assignment_id: string;
    github_repo_url?: string | null;
    file_path?: string | null;
    commit_hash?: string | null;
};
```

Tuy nhiên khi rà soát `frontend/src` ngoài thư mục `generated`, chưa thấy màn hình thật nào đang gọi `submitCodeCodeSubmissionsPost`. Nghĩa là backend flow đã có, SDK frontend đã sinh ra, nhưng nếu demo thao tác trên UI thì cần có form nhập GitHub URL và gọi endpoint này.

Flow UI cần có nếu bổ sung:

```text
Màn hình assignment
  -> ô nhập GitHub repo URL
  -> nút Nộp bài
  -> gọi submitCodeCodeSubmissionsPost
  -> hiển thị status/score
  -> gọi getSubmissionDetail hoặc getSubmissionHistory để xem feedback
```

### 10.16. Chi tiết lấy lại kết quả sau khi nộp

Lấy chi tiết một lần nộp:

```text
GET /code-submissions/{submission_id}
```

Service:

```python
CodeSubmissionService.get_submission_detail(submission_id=...)
```

Trả về:

```python
{
    "submission": submission,
    "feedback": feedback,
}
```

Lấy lịch sử theo bài tập:

```text
GET /code-submissions/history/{assignment_id}
```

Service:

```python
CodeSubmissionService.get_submission_history(user_id=..., assignment_id=...)
```

Luồng:

- User thường chỉ xem lịch sử của chính mình.
- Admin có thể truyền `user_id` để xem của người khác.
- Kết quả sắp xếp theo `submitted_at desc`.

Lấy điểm cao nhất:

```text
GET /code-submissions/best-score/{assignment_id}
```

Service:

```python
CodeSubmissionService.get_best_score(user_id=..., assignment_id=...)
```

Luồng:

- Query `max(CodeSubmissions.score)`.
- Nếu chưa có điểm thì trả `0`.

### 10.17. Code submission xuất hiện ở dashboard/project như thế nào

File:

```text
backend/app/services/projects.py
```

Trong project summary, service lấy:

- Danh sách assignments của project.
- Danh sách `CodeSubmissions` theo assignment.
- Danh sách quiz attempts theo assignment.

Sau đó tính:

- `submission_count`: tổng số lần nộp code + quiz attempts.
- `is_submitted`: assignment đã có nộp bài hay chưa.
- `last_submitted_at`: lần nộp gần nhất.
- `best_score`: điểm code cao nhất nếu có.
- `submissions_total`: tổng số submission trong project.
- `progress_percentage`: tỷ lệ assignment đã có submission.

Khi xóa project:

```python
ProjectService.delete_project(...)
```

Service xóa theo thứ tự:

1. Lấy `assignment_ids`.
2. Lấy `submission_ids`.
3. Xóa `AICodeFeedback` theo `submission_ids`.
4. Xóa `CodeSubmissions`.
5. Xóa `Assignments`.

Điều này tránh lỗi khóa ngoại giữa `ai_code_feedback` và `code_submissions`.

### 10.18. Các lỗi có thể gặp trong flow GitHub

| Tình huống | Nơi phát hiện | Kết quả |
|---|---|---|
| Không có subscription | `UserSubscriptionService.check_subscription` | 403 |
| Assignment không tồn tại | `CodeSubmissionService.submit_code` | 404 |
| Assignment inactive | `CodeSubmissionService.submit_code` | 400 |
| Không gửi `github_repo_url` và không gửi `file_path` | `submit_code` | 400 |
| Link không phải GitHub | `GithubCodeReader._parse_github_url` | 400 |
| Link thiếu owner/repo | `GithubCodeReader._parse_github_url` | 400 |
| Repo không tồn tại/private | `_get_repo_metadata` | 404 |
| GitHub API lỗi | `_get_repo_metadata` hoặc `_download_repo_zip` | HTTP error tương ứng |
| Zip repo quá lớn | `_download_repo_zip` | 413 |
| Extract quá lớn | `_safe_extract` | 413 |
| Zip có path nguy hiểm | `_safe_extract` | 400 |
| Không tìm thấy file code hợp lệ | `read_code_repo` | 400 |
| AI trả không đúng JSON | `_parse_github_response` | fallback feedback text |
| Lỗi bất ngờ khi chấm | `_trigger_ai_grading` | status `failed`, 500 |

### 10.19. Những câu trả lời phản biện nhanh về flow GitHub

**Người dùng nộp code bằng cách nào?**

Người dùng gửi `assignment_id` và `github_repo_url` lên `POST /code-submissions`. Backend xác thực user, tạo bản ghi submission rồi tự động đọc repo GitHub để AI chấm.

**Code có được lưu toàn bộ vào DB không?**

Không. Backend tải repo về thư mục tạm, lọc file code, ghép nội dung để gửi AI. DB chỉ lưu metadata của submission, commit/ref và feedback AI. Source code đầy đủ không được lưu vào bảng riêng trong flow hiện tại.

**Repo được đọc bằng cách clone git hay cách nào?**

Không dùng `git clone`. Backend gọi GitHub API và tải zipball của repo/ref, sau đó extract vào thư mục tạm.

**Repo private có đọc được không?**

Có thể đọc nếu server cấu hình `GITHUB_TOKEN` có quyền đọc repo đó. Nếu không có token hoặc token không đủ quyền thì repo private sẽ bị GitHub trả 404/403.

**AI chấm dựa trên gì?**

AI chấm dựa trên đề bài trong `Assignments`, thông tin repo, branch/ref, commit và source code đã được lọc/ghép từ GitHub.

**Điểm cuối cùng tính thế nào?**

Điểm cuối cùng là trung bình của `code_quality_score`, `logic_score`, `performance_score`.

**Có lưu lịch sử nhiều lần nộp không?**

Có. Mỗi lần gọi `POST /code-submissions` tạo một bản ghi `CodeSubmissions` mới. Lịch sử lấy bằng `GET /code-submissions/history/{assignment_id}`.

**Hai người nộp cùng một repo có feedback giống nhau không?**

Không chắc giống hoàn toàn. Nếu cùng assignment, cùng repo, cùng commit, cùng model và cùng prompt thì nội dung có thể rất giống. Nhưng vì AI sinh tự nhiên, vẫn có thể có khác biệt nhỏ. Hệ thống không cache feedback theo repo/commit, mỗi submission sẽ gọi AI riêng.

**Có chống repo quá lớn không?**

Có. Hệ thống giới hạn zip, tổng dung lượng extract, số file, dung lượng từng file và tổng số ký tự gửi sang AI.

**Nếu AI lỗi thì bài nộp có mất không?**

Không. Submission đã được lưu trước khi gọi AI. Nếu lỗi khi chấm, submission chuyển sang `failed`.

**Frontend đã có UI nộp GitHub chưa?**

SDK frontend đã có hàm gọi API, nhưng hiện chưa thấy màn hình thực tế trong `frontend/src` gọi hàm đó. Nếu cần demo qua UI thì nên bổ sung form nộp link GitHub.

## 11. AI provider và chọn model theo gói

Hàm AI thống nhất:

```python
AITransactionService.chat(...)
```

File:

```text
backend/app/services/ai_transaction.py
```

Luồng:

1. `_get_current_plan(db, user_id)`:
   - Join `UserSubscriptions` và `PricingPlans`.
   - Lấy plan active.
2. `_check_plan_limit(db, user_id, plan)`:
   - Nếu không có plan thì 403.
   - Nếu token tháng đã dùng >= limit thì 403.
3. `_get_provider_config(plan)`:
   - Plan premium/plus/pro hoặc `price > 0` và có `PREMIUM_AI_API_KEY` thì dùng premium provider.
   - Nếu không thì dùng Groq.
4. `AIProviderService.chat(...)`:
   - Gọi OpenAI-compatible API.
5. `_save_ai_usage_log(...)`:
   - Lưu model, token, action type vào `AIUsageLogs`.

Cấu hình model hiện ở `backend/app/core/config.py`:

- `GROQ_MODEL = "llama-3.1-8b-instant"`
- `PREMIUM_AI_PROVIDER = "cerebras"`
- `PREMIUM_AI_MODEL = "gpt-oss-120b"`

Điểm phản biện:

> Backend không hard-code một nhà cung cấp AI trong từng chức năng. Các chức năng gọi qua `AITransactionService`, còn service này tự chọn provider dựa theo gói của người dùng.

## 12. Luồng subscription và giới hạn

### 12.1. Kiểm tra subscription

Hàm:

```python
UserSubscriptionService.check_subscription(user_id)
```

Luồng:

1. `_get_active_subscription`.
2. Kiểm tra `end_date`.
3. Lấy `PricingPlans`.
4. Tính tổng token AI tháng hiện tại từ `AIUsageLogs`.
5. Nếu plan có `ai_usage_limit`, tính `remaining_tokens`.
6. Nếu vượt limit thì 403.

### 12.2. Project limit

Hàm:

```python
ProjectService.project_limit(session, user_id)
```

Luồng:

1. Lấy plan hiện tại.
2. Đọc `max_project`.
3. Đếm số project user sở hữu.
4. Nếu đã đạt limit thì chặn tạo project.

### 12.3. AI usage log

Mỗi lần AI gọi qua `AITransactionService.chat`, service tạo bản ghi:

```python
AIUsageLogs(
    user_id=user_id,
    project_id=project_id,
    action_type=action_type,
    model_name=provider_response.model_name,
    tokens_used=provider_response.tokens_used,
)
```

Các `action_type` quan trọng:

- `generate_curriculum`
- `generate_questions`
- `generate_quiz_questions`
- `code_review`
- `generate_analysis`
- `generate_feedback`

## 13. Luồng thanh toán và nâng gói

### 13.1. Tạo thanh toán MoMo

Endpoint:

```text
POST /payments/momo/create
```

Route gọi:

```python
MomoPaymentService(session).create_payment(user_id, plan_id)
```

Luồng:

1. Query `PricingPlans`.
2. Nếu plan inactive thì 400.
3. Nếu giá <= 0:
   - Không tạo thanh toán.
   - Gọi `PricingPlanService.subscribe_plan`.
4. Nếu có phí:
   - Kiểm tra cấu hình MoMo.
   - Tạo `order_id`, `request_id`.
   - Ký HMAC bằng `_sign`.
   - Tạo `PaymentTransactions` status `pending`.
   - Gọi endpoint MoMo.
   - Lưu `pay_url`, `deeplink`, `qr_code_url`.
   - Trả link thanh toán cho frontend.

### 13.2. MoMo IPN callback

Endpoint:

```text
POST /payments/momo/ipn
```

Route gọi:

```python
MomoPaymentService.handle_ipn(data)
```

Luồng:

1. Verify chữ ký:

```python
_build_ipn_signature(data)
hmac.compare_digest(received_signature, expected_signature)
```

2. Query `PaymentTransactions` theo `orderId` và `requestId`.
3. Nếu transaction đã paid thì trả success.
4. Nếu `resultCode == 0` và amount khớp:
   - Set transaction `paid`.
   - Set `paid_at`.
   - Gọi `PricingPlanService.subscribe_plan`.
5. Nếu lỗi thì set `failed`.

## 14. Luồng xóa project

Endpoint:

```text
DELETE /projects/{project_id}
```

Route gọi:

```python
ProjectService.delete_project(...)
```

Luồng:

1. Kiểm tra project tồn tại.
2. Kiểm tra user là owner.
3. Lấy toàn bộ dữ liệu liên quan:
   - curriculum ids
   - module ids
   - material ids
   - assignment ids
   - submission ids
   - question ids
   - attempt ids
   - result ids
4. Xóa theo thứ tự tránh lỗi foreign key:
   - answers
   - question options
   - code feedback
   - AI analysis
   - material chunks
   - questions
   - code submissions
   - assignments
   - assessment results
   - attempts
   - learning materials
   - curriculum modules
   - curriculums
   - AI generated sources
   - AI usage logs
   - project

Điểm phản biện:

> Project delete không chỉ xóa project. Nó dọn toàn bộ dữ liệu phụ thuộc để tránh dữ liệu rác.

## 15. Trả lời nhanh các câu hỏi phản biện thường gặp

### 15.1. File upload được lưu ở đâu?

File thật lưu ở:

```text
backend/app/storage/
```

DB chỉ lưu đường dẫn trong `LearningMaterials.file_path`.

### 15.2. Hàm nào lưu file?

```python
storage.save_uploaded_file(upload_file)
```

### 15.3. Hàm nào tạo metadata DB cho tài liệu?

```python
LearningMaterialService.create_material(...)
```

Tạo bản ghi trong bảng:

```text
learning_materials
```

### 15.4. Hàm nào đọc text từ file?

```python
file_parser.extract_text(path_or_url)
```

Tùy loại file nó gọi:

- PDF text: `_extract_text_from_pdf_layer`, `extract_text_pdf`
- PDF scan/image: `extract_text_with_ocr`
- DOCX/PPTX: `_extract_zip_xml_text`
- Web: `_extract_text_from_web`

### 15.5. Hàm nào làm sạch text?

```python
text_cleaner.clean_vietnamese_text(...)
ai_service.clean_learning_material_text(...)
```

### 15.6. Hàm nào chia nhỏ tài liệu?

```python
MaterialChunkService.save_material_chunk(...)
  -> ai_service._split_passages(text)
```

Lưu vào bảng:

```text
material_chunks
```

### 15.7. Hàm nào lấy tài liệu từ DB để sinh câu hỏi?

```python
QuestionService._collect_assignment_source_text(...)
```

Nó lấy `MaterialChunk` theo material của project rồi ghép lại.

### 15.8. Hàm nào lấy tài liệu để sinh curriculum?

```python
CurriculumGenerationService._collect_project_material_text(...)
```

Nó query `LearningMaterials` theo project, rồi extract text từ file/link.

### 15.9. Hàm nào gọi AI sinh câu hỏi?

```python
QuestionService._generate_question_payloads_from_source(...)
  -> AITransactionService.chat(...)
```

### 15.10. Hàm nào gọi AI chấm code?

```python
CodeSubmissionService._trigger_ai_grading(...)
  -> AITransactionService.chat(action_type="code_review")
```

### 15.11. Hàm nào chọn Groq hay Cerebras?

```python
AITransactionService._get_provider_config(plan)
```

Plan Free dùng Groq, plan trả phí/premium dùng provider premium nếu có key.

### 15.12. Nếu 2 người dùng dùng cùng một file thì câu hỏi có giống nhau không?

Phụ thuộc ngữ cảnh:

- Nếu cùng một assignment/module đã có câu hỏi trong DB, hệ thống sẽ reuse câu hỏi đó, nên kết quả giống.
- Nếu mỗi người ở project/assignment/module khác nhau và hệ thống gọi AI mới, câu hỏi có thể khác dù tài liệu giống, vì AI có tính sinh ngẫu nhiên.
- `temperature=0.1` giúp giảm độ ngẫu nhiên, nhưng không đảm bảo 100% giống nhau.

### 15.13. Vì sao phải chunk tài liệu?

Chunk giúp:

- Không phải đọc/parse lại file mỗi lần tạo câu hỏi.
- Dễ chọn đoạn liên quan.
- Giảm input quá dài khi gọi AI.
- Tái sử dụng nội dung cho nhiều chức năng.

### 15.14. Vì sao không đưa toàn bộ file vào AI?

Vì file có thể lớn, scan lỗi, chứa header/footer/noise. Hệ thống cần:

1. Lưu file.
2. Extract text.
3. Làm sạch.
4. Chia chunk.
5. Chọn context phù hợp.
6. Mới gọi AI.

Quy trình này giúp giảm chi phí, giảm lỗi token limit và tăng chất lượng câu hỏi/bài học.

### 15.15. GitHub repo được bảo vệ thế nào?

`GithubCodeReader` có:

- Validate domain GitHub.
- Validate owner/repo.
- Giới hạn zip download.
- Giới hạn dung lượng extract.
- Chống path traversal khi extract zip.
- Bỏ qua thư mục không cần như `node_modules`, `venv`, `dist`, `build`.
- Giới hạn số file và tổng ký tự gửi vào AI.

## 16. Checklist nói khi demo/phản biện

Khi trình bày, nên đi theo thứ tự:

1. User đăng nhập, token cookie được kiểm tra bằng `Authen.get_current_user`.
2. User tạo project, hệ thống kiểm tra giới hạn project theo plan.
3. User upload tài liệu:
   - file lưu vào `backend/app/storage`
   - metadata lưu `learning_materials`
   - text được extract, clean, chunk
   - chunk lưu `material_chunks`
4. User generate curriculum:
   - lấy tài liệu project
   - extract/clean full text
   - tìm mục lục hoặc fallback outline
   - tạo curriculum/modules
   - generate preview modules
5. User mở bài học:
   - module chưa ready thì generate
   - có thể prefetch module tiếp theo
6. User làm quiz:
   - nếu chưa có câu hỏi thì AI sinh câu hỏi từ source
   - validate JSON, option, source quote
   - submit quiz, tính điểm, tạo assessment result
7. User nộp code:
   - đọc repo GitHub
   - lọc file code
   - gọi AI chấm
   - lưu feedback và score
8. AI usage:
   - mọi lần gọi qua `AITransactionService` sẽ log token/model/action
   - provider chọn theo plan
9. Payment:
   - plan miễn phí subscribe ngay
   - plan trả phí qua MoMo/card
   - IPN MoMo verify chữ ký trước khi nâng gói

## 17. File nên mở khi phản biện trực tiếp

Nếu hội đồng hỏi chi tiết, mở các file này:

- Upload tài liệu:
  - `backend/app/api/route/LearningMaterials.py`
  - `backend/app/services/LearningMaterials.py`
  - `backend/app/services/storage.py`
  - `backend/app/services/material_chunk.py`
  - `backend/app/services/file_parser.py`
- Làm sạch/chia đoạn:
  - `backend/app/services/text_cleaner.py`
  - `backend/app/services/ai_service.py`
- Sinh curriculum:
  - `backend/app/api/route/curriculum.py`
  - `backend/app/services/curriculum.py`
  - `backend/app/services/curriculum_generate.py`
- Sinh câu hỏi:
  - `backend/app/api/route/questions.py`
  - `backend/app/services/questions.py`
  - `backend/app/services/quiz_templates.py`
- Gọi AI/provider:
  - `backend/app/services/ai_transaction.py`
  - `backend/app/services/ai_provider_client.py`
  - `backend/app/services/ai_Usage_Log.py`
- Chấm code GitHub:
  - `backend/app/api/route/code_submissions.py`
  - `backend/app/services/code_submissions.py`
  - `backend/app/services/github_code_reader.py`
  - `backend/app/services/Ai_code_feedback.py`
- Payment:
  - `backend/app/api/route/payments.py`
  - `backend/app/services/momo_payment.py`
  - `backend/app/services/Pricing_plans.py`
