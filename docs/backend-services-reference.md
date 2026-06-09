# Tài liệu phản biện tầng Backend Service

Tài liệu này mô tả các service trong `backend/app/services`. Mục tiêu là giúp giải thích khi phản biện: mỗi service chịu trách nhiệm gì, hàm nào được gọi trong luồng nghiệp vụ, dữ liệu vào/ra là gì, có tác động gì tới database hoặc API bên ngoài, và cần lưu ý điểm nào.

## 1. Vai trò của tầng Service

Tầng service là nơi chứa logic nghiệp vụ chính của backend. Route/API chỉ nhận request, xác thực user và gọi service tương ứng. Service chịu trách nhiệm:

- Kiểm tra dữ liệu đầu vào và quyền sử dụng.
- Đọc/ghi database qua `Session`.
- Gọi các service phụ như AI, parser, payment, GitHub.
- Chuẩn hóa dữ liệu trả về cho frontend.
- Bảo vệ quota, rate limit, giới hạn gói, giới hạn file hoặc repository.

Các nhóm service chính:

- **Người dùng, gói và giới hạn**: `users.py`, `Pricing_plans.py`, `user_subscriptions.py`, `ai_Usage_Log.py`.
- **Project và tài liệu học**: `projects.py`, `LearningMaterials.py`, `storage.py`, `file_parser.py`, `material_chunk.py`, `text_cleaner.py`.
- **Curriculum và bài học AI**: `curriculum.py`, `curriculum_generate.py`, `curriculum_Module.py`, `ai_service.py`.
- **Quiz, câu hỏi và đánh giá năng lực**: `questions.py`, `question_option.py`, `answers.py`, `AssessmentAttempt.py`, `assessment_Result.py`, `ai_analysis.py`.
- **Chấm code qua GitHub**: `code_submissions.py`, `github_code_reader.py`, `Ai_code_feedback.py`.
- **Thanh toán và thống kê**: `momo_payment.py`, `order.py`, `admin_stats.py`.

## 2. Luồng nghiệp vụ chính

### 2.1. Upload tài liệu và tạo chunk

1. `LearningMaterialService.create_material` nhận `project_id`, `title`, file upload hoặc link ngoài.
2. Nếu là file, `save_uploaded_file` lưu file vào `backend/app/storage` với tên UUID để tránh trùng tên.
3. Tạo bản ghi `LearningMaterials` trong DB.
4. Gọi `MaterialChunkService.save_material_chunk`.
5. `MaterialChunkService` dùng `extract_text` để đọc nội dung từ PDF/DOCX/PPTX/TXT/image/web.
6. Nội dung được làm sạch bằng `clean_learning_material_text`, sau đó chia đoạn bằng `_split_passages`.
7. Các đoạn được lưu vào bảng `material_chunks`.

Điểm phản biện: hệ thống không đưa nguyên file vào AI ngay. File được lưu vật lý, metadata lưu trong DB, nội dung được trích xuất và chia chunk để tái sử dụng cho sinh curriculum/câu hỏi.

### 2.2. Sinh curriculum và bài học

1. `CurriculumService.generate_lessons_for_project` gọi `CurriculumGenerationService.generate_from_curriculum`.
2. Service gom toàn bộ text từ tài liệu project bằng `_collect_project_material_text`.
3. Nếu tài liệu có mục lục, `extract_curriculum_outline_from_toc` sinh outline từ mục lục.
4. Nếu không có mục lục, `generate_curriculum_outline_fallback` tạo outline fallback từ heading hoặc nội dung đã làm sạch.
5. Tạo `Curriculums` và các `CurriculumModules` ở trạng thái `pending`.
6. Chỉ generate trước một số module preview để giảm thời gian chờ.
7. Khi người dùng mở bài, `ensure_module_ready` sẽ generate nội dung module nếu chưa sẵn sàng.
8. Sau khi có module, `_ensure_question_set_for_modules` sinh câu hỏi quiz tương ứng.

Điểm phản biện: hệ thống dùng chiến lược lazy generation. Không generate toàn bộ bài học ngay lập tức, tránh timeout và giảm chi phí AI.

### 2.3. Sinh quiz và nộp quiz

1. `QuestionService.get_assignment_quiz` hoặc `get_module_quiz` đảm bảo câu hỏi đã tồn tại.
2. Nếu chưa có hoặc câu hỏi cũ là template/generic, service gọi AI để sinh câu hỏi dựa trên source text.
3. AI phải trả JSON có câu hỏi, 4 option, `correct_index`, `source_quote`.
4. Service kiểm tra `source_quote` phải nằm trong tài liệu gốc để giảm hallucination.
5. Khi submit, `submit_assignment_quiz` hoặc `submit_module_quiz` tạo `AssessmentAttempt`, lưu `Answers`, tính điểm phần trăm.
6. `AssessmentResultService.create_from_attempt` tính điểm trọng số và readiness level.

Điểm phản biện: câu hỏi không chỉ dựa vào prompt tự do. Có kiểm tra JSON, số option, đáp án đúng duy nhất và quote gốc trong tài liệu.

### 2.4. Chấm code qua GitHub

1. `CodeSubmissionService.submit_code` tạo bản ghi `CodeSubmissions`.
2. Nếu có `github_repo_url`, service gọi `_trigger_ai_grading`.
3. `GithubCodeReader.read_code_repo` validate URL, lấy metadata repo, commit hash, tải zip, extract an toàn, lọc file code.
4. Nội dung file code được gom thành `combined_content`.
5. `CodeSubmissionService._build_code_review_prompt` tạo prompt tiếng Việt, yêu cầu AI trả JSON.
6. `AITransactionService.chat` chọn provider theo gói:
   - Free hoặc không premium: Groq.
   - Plus/Pro/Premium hoặc plan có giá > 0 và có key premium: provider premium, hiện là Cerebras theo cấu hình.
7. `AICodeFeedbackService.create` lưu feedback, score từng phần, score trung bình và cập nhật trạng thái submission.

Điểm phản biện: có giới hạn kích thước repo, giới hạn số file, giới hạn tổng ký tự, chống zip path traversal, có lưu commit hash để biết phiên bản code đã chấm.

## 3. Service người dùng, gói và quota

### 3.1. `users.py` - `UserService`

- `_dump_payload(schema_obj)`: Chuyển Pydantic/SQLModel schema thành dict bằng `model_dump` hoặc `dict`. Dùng để service không phụ thuộc chặt vào version Pydantic.
- `get_users(session, query_params)`: Lấy danh sách user có phân trang, sort, search theo email. Có giới hạn `page_size` tối đa 100 và whitelist field sort.
- `get_by_id(session, user_id)`: Lấy user theo id, không có thì trả 404.
- `create_user(session, user_in)`: Tạo user mới. Kiểm tra email, trùng email, password bắt buộc; hash password trước khi lưu.
- `update_user(session, user_id, user_in)`: Admin cập nhật user. Nếu đổi email thì kiểm tra trùng; nếu có password thì hash lại.
- `update_current_user(session, user_id, user_in)`: User tự cập nhật profile, chỉ cho phép các field an toàn như `account_name`, `contact_email`, `contact_phone`, `avatar_url`.
- `delete_user(session, user_id)`: Xóa user. Nếu model có `is_deleted` thì soft delete, nếu không thì hard delete.

### 3.2. `Pricing_plans.py` - `PricingPlanService`

- `__init__(session)`: Lưu DB session cho toàn bộ service.
- `_dump_payload(schema_obj)`: Chuẩn hóa schema đầu vào thành dict.
- `_normalize_payload(payload)`: Đồng bộ tên field frontend/backend, ví dụ `max_projects` thành `max_project`, `badge_text` thành `bagde_text`.
- `_serialize_plan(plan)`: Trả plan dạng dict, gồm cả alias `max_project/max_projects` và `bagde_text/badge_text`.
- `_is_subscription_active(subscription)`: Kiểm tra subscription còn hiệu lực dựa trên `is_active` và `end_date`.
- `_get_active_subscription(user_id)`: Lấy subscription active mới nhất của user.
- `get_pricing_plans()`: Lấy danh sách plan, sort theo `display_order`, `price`, `name`.
- `get_current_subscription(user_id)`: Trả subscription hiện tại kèm thông tin plan.
- `create_pricing_plan(plan_in)`: Tạo plan; bắt buộc tên, không trùng tên, giá không âm.
- `update_pricing_plan(plan_id, plan_in)`: Cập nhật plan; kiểm tra trùng tên, cập nhật `update_at`.
- `check_project_limit(user_id)`: Kiểm tra user còn quyền tạo project theo `max_project` của plan.
- `check_ai_limit(user_id)`: Kiểm tra tổng token AI tháng hiện tại có vượt `ai_usage_limit` không.
- `subscribe_plan(user_id, plan_id)`: Gán user vào plan. Nếu đã dùng cùng plan thì trả thông báo; nếu đang có plan khác thì kết thúc plan cũ và tạo subscription mới.

### 3.3. `user_subscriptions.py` - `UserSubscriptionService`

- `__init__(session)`: Lưu session.
- `_is_active(subscription)`: Subscription active nếu chưa bị tắt và chưa hết hạn.
- `_get_active_subscription(user_id)`: Lấy subscription active mới nhất.
- `subscribe(user_id, plan_id, duration_days=30)`: Kết thúc các subscription cũ, tạo subscription mới có `end_date = now + duration_days`.
- `check_subscription(user_id)`: Kiểm tra user có subscription hợp lệ và plan active; đồng thời tính `tokens_used` và `remaining_tokens`.
- `cancel_subscription(user_id)`: Hủy subscription hiện tại bằng cách set `end_date=now` và `is_active=False` nếu có field.
- `get_current_plan(user_id)`: Trả tên plan, giới hạn AI, token đã dùng, token còn lại và ngày hết hạn.

### 3.4. `ai_Usage_Log.py` - `AIUsageService`

- `calculate_cost(model_name, tokens)`: Tính chi phí ước lượng dựa trên bảng `MODEL_PRICING`. Token âm được đưa về 0.
- `log_usage(session, user_id, project_id, action_type, model_name, tokens_used)`: Lưu bản ghi `AIUsageLogs`, gồm token, model, action và cost.
- `get_monthly_usage(session, user_id)`: Tính tổng token AI của user trong tháng hiện tại.
- `check_quota(session, user_id, tokens_required)`: Dùng `UserSubscriptionService.check_subscription`; nếu token yêu cầu lớn hơn số còn lại thì trả 403.
- `check_rate_limit(session, user_id, action_type)`: Giới hạn số lần gọi theo ngày cho một số action như `generate_analysis`, `generate_feedback`, `generate_curriculum`.
- `admin_dashboard_stats(session)`: Tổng hợp token, cost và top 5 user dùng AI nhiều nhất.

## 4. Service project và tài liệu

### 4.1. `projects.py` - `ProjectService`

- `_has_table(session, table_name)`: Kiểm tra bảng có tồn tại trong DB không. Dùng để service chịu được khác biệt migration.
- `_safe_exec_all(session, statement)`: Chạy query, nếu lỗi SQLAlchemy thì trả list rỗng.
- `_safe_exec_first(session, statement)`: Chạy query lấy một bản ghi, lỗi thì trả `None`.
- `_delete_records(session, model, records, seen_ids)`: Xóa danh sách record, tránh xóa trùng id.
- `_serialize_datetime(value)`: Chuyển `datetime` sang ISO string hoặc `None`.
- `_latest_datetime(*values)`: Lấy datetime mới nhất trong các giá trị hợp lệ.
- `_dump_payload(schema_obj)`: Chuẩn hóa schema request thành dict.
- `_resolve_user_id(request, user_id)`: Lấy user id từ tham số hoặc `request.state.user_id`; thiếu thì trả 401.
- `_can_access_project(session, project, user_id)`: Cho phép truy cập nếu là owner, từng làm assessment, có assessment result hoặc từng submit code vào assignment của project.
- `get_project(session, project_id, request, user_id)`: Lấy chi tiết project và owner email, có kiểm tra quyền.
- `get_dashboard_overview(session, request, user_id)`: Gom dashboard học tập: project sở hữu/tham gia, assignment, submission code, quiz attempt, materials, assessment result, AI analysis, tiến độ và next action.
- `create_project(session, project_data, request, user_id)`: Kiểm tra limit theo plan rồi tạo project mới.
- `update_project(session, project_id, project_data, request, user_id)`: Chỉ owner được sửa tên/mô tả project.
- `delete_project(session, project_id, request, user_id)`: Chỉ owner được xóa; xóa cascade thủ công các dữ liệu liên quan như curriculum, module, material, chunk, question, option, answer, attempt, result, AI analysis, code submission, feedback, usage log.
- `_get_current_plan(session, user_id)`: Tìm plan active của user; nếu không có thì fallback về free plan active.
- `project_limit(session, user_id)`: Chặn tạo project nếu số project hiện tại >= `max_project`.

Điểm phản biện: xóa project được xử lý thủ công để đảm bảo dọn dữ liệu phụ thuộc, tránh orphan record nếu DB chưa cấu hình cascade đầy đủ.

### 4.2. `LearningMaterials.py` - `LearningMaterialService`

- `__init__(session)`: Lưu session.
- `_dump_payload(schema_obj)`: Chuẩn hóa input update.
- `create_material(project_id, title, external_link, file_path, current_user)`: Kiểm tra project tồn tại, chỉ nhận một trong hai nguồn file/link, lưu file nếu có, tạo `LearningMaterials`, sau đó cố gắng tạo chunk.
- `get_materials_by_project(project_id)`: Lấy danh sách tài liệu theo project, có hỗ trợ `is_active` nếu schema có.
- `get_material_detail(material_id)`: Lấy chi tiết tài liệu; ẩn tài liệu inactive.
- `update_material(material_id, material_in)`: Cập nhật tài liệu; đồng bộ `url` sang `external_link`; không cho vừa file vừa external link.
- `delete_material(material_id)`: Soft delete nếu có `is_active`, nếu không thì hard delete.

### 4.3. `storage.py`

- `save_uploaded_file(upload_file)`: Kiểm tra extension nằm trong `.pdf`, `.docx`, `.pptx`, `.txt`, `.jpg`, `.jpeg`, `.png`; lưu file vào `backend/app/storage` với tên UUID; trả `file_path` và `filename`.

Điểm phản biện: dùng UUID để tránh trùng tên file và tránh user điều khiển trực tiếp tên file lưu trên server.

### 4.4. `file_parser.py`

- `_extract_zip_xml_text(path, prefixes)`: Đọc nội dung XML trong file zip-based như DOCX/PPTX, gom text và làm sạch tiếng Việt.
- `_has_meaningful_text(text, min_alnum_chars)`: Kiểm tra text có đủ ký tự chữ/số để xem là extract thành công.
- `_configure_tesseract()`: Tìm tesseract từ settings, PATH hoặc đường dẫn phổ biến trên Windows.
- `_iter_poppler_candidates()`: Tạo danh sách đường dẫn Poppler ứng viên để OCR PDF scan.
- `_ocr_image(image)`: Convert ảnh sang grayscale, phóng to 2 lần, OCR bằng Tesseract với ngôn ngữ cấu hình.
- `_extract_text_from_web(url)`: Tải HTML bằng requests, dùng BeautifulSoup lấy text.
- `_extract_text_from_pdf_layer(file_path)`: Thử đọc text PDF bằng PyPDF2.
- `extract_text_pdf(file_path)`: Thử đọc PDF bằng pdfplumber.
- `extract_text_with_ocr(file_path)`: OCR ảnh hoặc PDF scan; thử nhiều Poppler path.
- `extract_text(path_or_url)`: Hàm entry chính. Tự nhận diện web/txt/pdf/docx/pptx/image và gọi parser phù hợp.

### 4.5. `material_chunk.py` - `MaterialChunkService`

- `__init__(session)`: Lưu session.
- `save_material_chunk(material_id, text=None)`: Nếu material đã có chunk thì trả chunk cũ; nếu chưa, lấy text từ tham số hoặc extract từ file/link; làm sạch rồi chia passage; lưu `MaterialChunk` theo `chunk_index`.

### 4.6. `text_cleaner.py`

- `_fold_vietnamese(value)`: Bỏ dấu tiếng Việt để phục vụ so khớp.
- `_iter_combining_marks(value)`: Lặp các dấu tổ hợp Unicode.
- `has_vietnamese_mark(text)`: Kiểm tra text có dấu tiếng Việt hoặc chữ `đ`.
- `_has_vietnamese_tone(text)`: Kiểm tra có thanh điệu.
- `_is_vietnamese_vowel(char)`: Kiểm tra ký tự là nguyên âm tiếng Việt.
- `_contains_folded_vowel(value)`: Kiểm tra chuỗi sau bỏ dấu có nguyên âm.
- `_split_initial_and_rhyme(folded_syllable)`: Tách phụ âm đầu và vần.
- `_is_valid_folded_rhyme(rhyme)`: Kiểm tra vần có hợp lệ theo tập âm tiết đã khai báo.
- `_is_plausible_vietnamese_syllable(value)`: Kiểm tra một chuỗi có giống âm tiết tiếng Việt không.
- `_is_initial_fragment(left)`: Xác định mảnh bên trái có thể là phụ âm đầu bị tách.
- `_is_likely_split_vowel_sequence(left, right)`: Nhận diện các cụm nguyên âm bị OCR tách.
- `should_join_vietnamese_fragment(left, right)`: Quyết định có nên nối hai mảnh từ bị tách không.
- `clean_vietnamese_text(text)`: Hàm làm sạch chính: normalize Unicode, chuẩn hóa khoảng trắng, nối fragment tiếng Việt bị tách, sửa khoảng trắng quanh dấu câu, bỏ dòng trống thừa.
- Nested `_join_fragment(match)`: Helper bên trong `clean_vietnamese_text`, quyết định nối hoặc giữ nguyên một match regex.

## 5. Service curriculum và bài học

### 5.1. `curriculum.py` - `CurriculumService`

- `_set_if_present(model_obj, field_name, value)`: Set field nếu model có field đó; dùng để tương thích nhiều schema.
- `_dump_payload(schema_obj)`: Chuẩn hóa payload.
- `create_curriculum(session, curriculum_in)`: Kiểm tra project, làm sạch title/overview, tạo `Curriculums`.
- `get_curriculums_by_project(session, project_id)`: Lấy danh sách curriculum theo project.
- `get_curriculum_detail(session, curriculum_id)`: Lấy curriculum và gắn danh sách modules đã sort.
- `update_curriculum(session, curriculum_id, curriculum_in)`: Cập nhật field hợp lệ, làm sạch title/overview.
- `delete_curriculum(session, curriculum_id)`: Soft delete nếu có `is_active`, nếu không hard delete.
- `get_lessons_by_curriculum(session, project_id)`: Lấy modules của curriculum mới nhất trong project.
- `_build_module_description(module_data, index)`: Sinh description module từ `description`, `content` hoặc list `lessons`.
- `generate_lessons_for_project(session, project_id, force_regenerate, user_id)`: Entry gọi `CurriculumGenerationService.generate_from_curriculum`.
- `generate_curriculum(session, project_id, generated_by)`: Alias cho generate lessons, truyền user id qua `generated_by`.
- `generate_lessions(session, project_id, user_id)`: Alias giữ tương thích tên cũ bị typo.

### 5.2. `curriculum_generate.py` - `CurriculumGenerationService`

- `_get_latest_curriculum(session, project_id)`: Lấy curriculum mới nhất của project.
- `_get_curriculum_modules(session, curriculum_id)`: Lấy modules của một curriculum theo order.
- `_get_project_curriculum_modules(session, project_id)`: Lấy tất cả module thuộc project qua join curriculum.
- `_delete_questions_for_modules(session, modules)`: Xóa answers/options/questions liên quan tới các module trước khi regenerate.
- `_has_newer_materials(session, project_id, curriculum)`: Kiểm tra có material mới hơn curriculum không.
- `_sync_curriculum_progress(session, curriculum, modules)`: Cập nhật `total_module` và `ready_module`.
- `_get_project_or_404(session, project_id)`: Lấy project hoặc trả 404.
- `_collect_project_material_text(session, project_id)`: Gom text từ tất cả learning material của project; extract và clean từng file/link.
- `_get_module_context_or_404(session, module_id)`: Lấy module và curriculum cha.
- `_question_assignment_field_name()`: Trả tên field assignment trong `Questions`: `assignment_id` hoặc `assignments_id`.
- `_question_assignment_field()`: Trả object field tương ứng để query.
- `_get_or_create_lesson_criteria(session)`: Lấy/tạo criteria mặc định `Lesson comprehension`.
- `_get_or_create_question_assignment(session, project_id, curriculum)`: Tạo assignment chứa bộ câu hỏi cho curriculum.
- `_build_questions_for_module(module)`: Hiện trả list rỗng; giữ lại như extension point.
- `_create_question_options(session, question, options)`: Lưu options cho question.
- `_ensure_question_set_for_modules(session, project_id, curriculum, modules, user_id)`: Đảm bảo mỗi module có đủ câu hỏi; nếu câu hỏi cũ thiếu/generic/không dấu thì sinh lại từ nội dung module.
- `_create_pending_modules(session, curriculum, modules, preview_count)`: Tạo module pending từ outline; đánh dấu preview cho một số module đầu.
- `_enrich_module_descriptions_from_source(modules, full_text)`: Bổ sung description module bằng đoạn source phù hợp từ tài liệu.
- `_generate_module_content(session, curriculum, module, full_text, mark_preview)`: Generate nội dung module; set `generating`, sau đó `ready` hoặc `failed`; cập nhật progress.
- `_ensure_preview_modules_ready(session, curriculum, modules, project_id, preview_count)`: Generate sẵn các module preview đầu tiên.
- `generate_from_curriculum(session, project_id, preview_count, force_regenerate, user_id)`: Entry chính tạo/reuse curriculum. Có logic reuse nếu curriculum hiện tại còn mới; nếu force thì xóa câu hỏi cũ; nếu không có mục lục thì fallback.
- `ensure_module_ready(session, module_id)`: Khi mở module, generate nội dung nếu module chưa ready.
- `prefetch_next_modules(session, module_id, limit)`: Generate trước các module tiếp theo ở trạng thái pending/failed.
- `prefetch_next_modules_background(module_id, limit, user_id)`: Mở session riêng để prefetch background và log AI usage qua context.

### 5.3. `curriculum_Module.py` - `CurriculumModuleService`

- `get_module_detail(session, module_id)`: Lấy module hoặc 404.
- `create_module(session, curriculum_id, title, description, order_index)`: Tạo module thủ công; nếu không truyền order thì lấy max + 1; tăng `total_module`.
- `delete_module(session, module_id)`: Xóa module; bỏ liên kết material chunks; giảm `total_module` và `ready_module` nếu cần.

## 6. Service AI lõi

### 6.1. `ai_provider_client.py`

- `AIProviderClient`: Dataclass chứa provider, api_key, base_url, model.
- `AIProviderResponse`: Dataclass chứa content, tokens_used, model_name, provider.
- `AIProviderService.chat(config, messages, response_format, temperature, max_completion_tokens)`: Wrapper gọi OpenAI-compatible API. Dùng được cho Groq/Cerebras vì đều dùng format OpenAI chat completion. Bắt rate limit thành 429 và lỗi provider thành 502.

### 6.2. `ai_transaction.py` - `AITransactionService`

- `chat(db, user_id, project_id, action_type, messages, response_format, temperature, max_completion_tokens)`: Entry thống nhất cho AI transaction. Lấy plan hiện tại, kiểm tra quota, chọn provider, gọi AI, lưu usage log, trả nội dung text.
- `_get_current_plan(db, user_id)`: Join `UserSubscriptions` và `PricingPlans` để lấy plan active.
- `_check_plan_limit(db, user_id, plan)`: Nếu không có plan thì 403; nếu đã dùng token >= limit thì 403.
- `_get_provider_config(plan)`: Plan premium/plus/pro hoặc plan có giá > 0 sẽ dùng premium provider nếu có key; còn lại dùng Groq.
- `_get_groq_config()`: Tạo config Groq từ settings; thiếu key thì trả 400.
- `_count_monthly_tokens(db, user_id)`: Tổng token tháng hiện tại.
- `_save_ai_usage_log(db, user_id, project_id, action_type, provider_response)`: Ghi `AIUsageLogs` sau mỗi lần gọi AI.

### 6.3. `ai_service.py`

File này chứa logic AI cũ và các helper xử lý tài liệu/curriculum. Có thể chia thành các nhóm:

**Nhóm tracking và gọi LLM**

- `AIResponseFormatError`: Exception riêng khi AI trả JSON sai format.
- `ai_usage_tracking_context(session, user_id, project_id, action_type)`: Context manager để các hàm `call_llm` bên trong tự log usage.
- `_extract_response_total_tokens(response)`: Lấy `usage.total_tokens` từ response AI.
- `_estimate_llm_tokens(*parts)`: Ước lượng token bằng `len(text)//4` khi provider không trả usage.
- `_log_llm_usage(response, prompt, system_prompt, content)`: Ghi usage log nếu đang nằm trong `ai_usage_tracking_context`.
- `_get_client()`: Tạo Groq client từ `GROQ_API_KEY`.
- `call_llm(prompt, system_prompt, temperature, max_completion_tokens, response_format)`: Gọi Groq trực tiếp, model mặc định `llama-3.1-8b-instant`, trả content.
- `_call_json(prompt, system_prompt, temperature, max_attempts, max_completion_tokens)`: Gọi LLM và parse JSON, retry nếu response sai format.

**Nhóm làm sạch text**

- `_legacy_clean_text(text)`: Wrapper cũ để làm sạch text và bỏ noise giáo trình/trang.
- `_fold_text(value)`: Bỏ dấu và lowercase để so khớp.
- `_compact_key(value)`: Chuẩn hóa text thành key gọn để so sánh/dedupe.
- `_line_alnum_ratio(line)`: Tỷ lệ ký tự chữ/số trong một dòng.
- `_is_noise_line(line)`: Nhận diện dòng noise như số trang, header/footer, dòng quá ít thông tin.
- `_has_vietnamese_mark(value)`, `_is_vietnamese_vowel(char)`, `_trailing_vietnamese_consonants(value)`, `_split_vietnamese_syllables(value)`, `_fix_ocr_split_letters(line)`: Các helper sửa lỗi OCR tiếng Việt, nhất là chữ bị tách.
- `clean_learning_material_text(text)`: Hàm làm sạch tài liệu chính: normalize, sửa ngắt dòng, bỏ header/footer lặp, bỏ noise, chuẩn hóa dấu câu.
- `clean_text_v2(text)`: Alias của `clean_learning_material_text`.

**Nhóm mục lục và outline**

- `_looks_like_toc_heading(line)`: Nhận diện dòng "Mục lục"/"Contents".
- `_clean_toc_title(title, remove_page_tail)`: Làm sạch title trong mục lục.
- `_toc_level(number)`: Suy ra cấp mục lục từ số dạng `1`, `1.2`, `Chương I`.
- `_parse_toc_entry(line)`: Parse một dòng thành `{number,title,level}` nếu giống mục lục.
- `_read_toc_entries_from(lines, start_index)`: Đọc nhiều dòng mục lục từ vị trí bắt đầu.
- `_find_toc_entries(cleaned_text)`: Tìm danh sách mục lục tốt nhất trong text.
- `_dedupe_toc_entries(entries)`: Loại entry trùng.
- `_select_toc_modules(entries)`: Chọn các entry thích hợp làm module.
- `_infer_curriculum_title(cleaned_text)`: Suy ra title curriculum từ các dòng đầu.
- `extract_curriculum_outline_from_toc(text)`: Tạo outline curriculum từ mục lục nếu có.

**Nhóm format nội dung học**

- `_strip_code_fences(content)`: Bỏ ``` khỏi response AI.
- `_truncate_preview(content, limit)`: Rút gọn preview log.
- `_normalize_block(block)`: Chuẩn hóa whitespace trong một block.
- `format_readable_paragraphs(text, max_sentences_per_paragraph)`: Chia text thành đoạn dễ đọc.
- `_replace_ocr_spacing_with_case(match, replacement)`: Helper giữ đúng hoa/thường khi thay các cụm OCR bị tách.
- `_fix_common_vietnamese_ocr_spacing(text)`: Sửa các lỗi spacing OCR tiếng Việt phổ biến.
- `_heading_candidate_needs_more_words(heading_candidate)`: Xác định heading có quá ngắn và cần ghép thêm từ hay không.
- `_body_start_repeats_heading_phrase(heading_candidate, body_candidate)`: Nhận diện body bị lặp lại cụm heading để tránh chia sai đoạn.
- `_insert_learning_heading_boundaries(text)`: Chèn ranh giới heading trong nội dung học.
- `_find_learning_body_start(text)`: Tìm vị trí bắt đầu phần thân bài sau heading.
- `_split_learning_heading_and_body(block)`: Tách một block thành heading và body.
- `_split_learning_sentences(text)`: Tách body thành câu.
- `_format_learning_body(text, max_sentences_per_paragraph)`: Gom câu thành đoạn ngắn dễ đọc.
- `format_learning_content_structure(text)`: Hàm format cuối cùng cho nội dung bài học, dùng các helper heading/body phía trên.

**Nhóm chọn passage/context**

- `_is_useful_passage(passage)`: Lọc passage hữu ích.
- `_chunk_text(text, max_chars)`: Cắt text dài thành chunk.
- `_split_passages(text)`: Chia text thành passages có ý nghĩa.
- `_extract_keywords(*parts, limit)`: Lấy keyword từ title/description.
- `_score_passage(passage, keywords)`: Chấm passage theo keyword.
- `_pick_evenly_spaced_indices(total, count)`: Chọn index phân bố đều.
- `_join_selected_passages(passages, indices, max_chars)`: Ghép passages theo giới hạn ký tự.
- `_select_passages_from_indices(passages, indices, max_chars)`: Chọn passage theo index.
- `_group_passages(passages, max_chars_per_group, max_groups)`: Gom passage thành nhóm cho xử lý batch.
- `_select_outline_passages(text, max_chars)`, `_build_outline_context(text, max_chars)`: Chọn context cho outline.
- `_build_module_context(text, module_title, module_description, max_chars)`, `_select_module_passages(...)`: Chọn context phù hợp cho module.

**Nhóm sinh outline/bài học**

- `_serialize_outline_chunk_result(chunk_result, chunk_index)`: Chuyển kết quả chunk outline thành text compact.
- `_serialize_lesson_chunk_result(chunk_result, chunk_index)`: Chuyển notes bài học thành text compact.
- `_build_learning_objectives(module_title, module_description)`: Tạo objectives fallback từ module.
- `_extract_json_candidate(content)`: Lấy JSON object từ response có thể lẫn text.
- `_parse_json_object(content)`: Parse JSON và raise `AIResponseFormatError` nếu sai.
- `_generate_outline_chunk_summary(chunk_text, chunk_index, total_chunks)`: Gọi AI tóm tắt một chunk để lấy module candidate.
- `_generate_lesson_chunk_notes(...)`: Gọi AI lấy notes học tập từ một chunk.
- `generate_curriculum_outline(text)`: Ưu tiên mục lục, fallback nếu không có.
- `generate_curriculum_outline_fallback(text)`: Sinh outline từ heading hoặc tạo một module chung nếu tài liệu không có cấu trúc.
- `generate_module_content(text)`: Alias tạo outline/module content theo flow cũ.
- `_toc_number_from_description(module_description)`, `_find_matching_toc_entry(...)`, `_line_matches_toc_entry(line, entry)`: Tìm section trong tài liệu khớp module.
- `_alnum_count(text)`, `_limit_source_text(text, max_chars)`: Đếm/lọc text source.
- `_extract_entry_section_text(lines, entries, entry_index, toc_end_index)`: Trích đoạn nội dung tương ứng mục lục.
- `_find_parent_toc_index(entries, entry_index)`: Tìm mục cha nếu mục con quá ngắn.
- `_extract_source_section(cleaned_text, module_title, module_description, max_chars)`: Lấy section nguồn phù hợp nhất cho module.
- `build_module_source_description(text, module_title, module_description, max_chars)`: Tạo mô tả module dựa trên source section.
- `generate_lesson_content_from_source(...)`: Tạo nội dung bài học trực tiếp từ source text đã chọn.
- `generate_lesson_content(...)`: Alias gọi `generate_lesson_content_from_source`.
- `generate_lesson_content_fallback(...)`: Fallback khi generate lesson chính lỗi.
- `call_lln(text)`: Tên cũ, gọi sinh outline từ text.
- `generate_lession_content(...)`: Tên cũ bị typo, alias của generate lesson.
- `assign_passages_to_modules(passages, modules)`: Gán passages cho modules theo keyword.
- `split_text_by_modules(text, modules)`: Chia text theo module.
- `assign_content_to_modules(text, modules)`: Trả modules kèm nội dung được gán.

## 7. Service quiz, câu hỏi và đánh giá

### 7.1. `questions.py` - `QuestionService`

- `_assignment_field()` và `_assignment_field_name()`: Tương thích schema cũ/mới giữa `assignment_id` và `assignments_id`.
- `_strip_code_fences(content)`, `_extract_json_candidate(content)`: Làm sạch response AI để parse JSON.
- `_rate_limit_retry_at()`, `_is_rate_limit_error(exc)`, `_mark_rate_limit_cooldown(exc)`: Cơ chế cooldown khi provider bị rate limit.
- `_create_question_record(session, assignment, criteria_id, content, question_type, explanation, generated_by)`: Tạo bản ghi question, làm sạch tiếng Việt và gắn assignment.
- `_get_or_create_lesson_criteria(session)`: Tạo criteria mặc định cho câu hỏi bài học.
- `_get_or_create_module_assignment(session, module, curriculum)`: Tạo assignment riêng cho quiz của module.
- `_build_module_questions(module)`: Hiện trả rỗng; extension point.
- `_is_legacy_unaccented_question_set(questions)`: Nhận diện bộ câu hỏi cũ không dấu.
- `_fold_for_matching(value)`: Bỏ dấu để so khớp text.
- `_is_generic_template_content(content)`, `_is_generic_template_question_set(questions)`, `_filter_generic_template_questions(questions)`: Nhận diện/lọc câu hỏi template chung chung.
- `_limit_source_text(source_text)`: Giới hạn source text cho prompt quiz.
- `_has_enough_source_text(source_text)`: Chỉ generate nếu đủ từ.
- `_extract_lesson_source_text(lesson_content)`: Ưu tiên phần "nội dung nguồn" trong lesson, bỏ phần câu hỏi ôn tập.
- `_create_template_questions(...)`: Hiện trả rỗng, do hệ thống ưu tiên câu hỏi AI bám source.
- `_coerce_correct_index(raw_value)`: Ép index đáp án đúng về 0-3.
- `_normalize_options(raw_options, correct_index)`: Chuẩn hóa option, yêu cầu đúng 4 option và đúng 1 đáp án đúng.
- `_create_option_records(session, question, raw_options)`: Tạo `QuestionOptions`.
- `_serialize_options(options, include_correct)`: Trả options cho frontend; ẩn đáp án đúng nếu làm quiz.
- `_parse_ai_questions(response)`: Parse list câu hỏi từ JSON AI.
- `_build_source_quiz_prompt(source_text)`: Prompt yêu cầu AI tạo câu hỏi trắc nghiệm bám tài liệu, có `source_quote`.
- `_source_contains_quote(source_text, source_quote)`: Kiểm tra quote AI đưa ra thật sự nằm trong source.
- `_normalize_ai_question_item(item, source_text)`: Validate từng câu hỏi AI: có dấu, không generic, 4 option, quote hợp lệ.
- `_generate_question_payloads_from_source(source_text, count, session, user_id, project_id)`: Gọi AI để sinh question payload; nếu có session/user/project thì đi qua `AITransactionService` để log quota/provider.
- `_create_source_questions(session, assignment, criteria_id, source_text, curriculum_module_id, generated_by, count, user_id)`: Tạo Questions và Options từ payload AI.
- `_collect_assignment_source_text(session, assignment, fallback_text)`: Lấy source từ `MaterialChunk` của project, fallback về mô tả assignment.
- `get_questions(session, assignment_id, include_correct)`: Lấy câu hỏi của assignment; có thể include đáp án đúng cho admin.
- `get_assignment_quiz(session, assignment_id, user_id)`: Đảm bảo assignment có câu hỏi rồi trả quiz cho frontend.
- `_ensure_assignment_questions(session, assignment, user_id)`: Sinh lại nếu thiếu câu hỏi hoặc câu hỏi cũ generic/không dấu.
- `_ensure_module_questions(session, module, curriculum, user_id)`: Tương tự assignment nhưng theo module bài học.
- `get_module_quiz(session, module_id, user_id)`: Trả quiz cho một bài học.
- `_build_quiz_evaluation(score, correct_count, total_questions)`: Tạo đánh giá high/medium/low và recommendation.
- `_serialize_assessment_result(result)`: Chuẩn hóa assessment result thành dict.
- `_create_quiz_assessment_result(session, attempt_id)`: Tạo assessment result sau khi submit quiz.
- `submit_assignment_quiz(session, assignment_id, user_id, answers)`: Validate đáp án, tạo attempt, lưu answers, tính điểm, tạo assessment result.
- `submit_module_quiz(session, module_id, user_id, answers)`: Submit quiz theo module.
- `create_question(session, assignment_id, criteria_id, content, generated_by, user_id)`: Sinh câu hỏi từ nội dung/material của assignment.

### 7.2. `question_option.py` - `QuestionOptionService`

- `_ensure_model_available()`: Trả 501 nếu model `QuestionOptions` chưa cấu hình.
- `_dump_payload(schema_obj)`: Chuẩn hóa payload.
- `create(session, question_id, option_in)`: Tạo option; với single choice thì không cho có hai option đúng.
- `update(session, option_id, option_in)`: Cập nhật option, cũng bảo vệ rule một đáp án đúng.
- `delete(session, option_id)`: Xóa option.
- `get_by_question(session, question_id)`: Lấy options theo question.

### 7.3. `answers.py` - `AnswerService`

- `_dump_payload(schema_obj)`: Chuẩn hóa input.
- `_set_if_present(model_obj, field_name, value)`: Set field tương thích schema.
- `_resolve_auto_score(session, question_id, selected_option_id, score, is_correct)`: Nếu chọn option, tự xác định đúng/sai và auto score 5 hoặc 1.
- `create(session, answer_in)`: Tạo answer trong attempt chưa submit; kiểm tra time limit, trùng câu hỏi, quyền user.
- `get_by_attempt_id(session, attempt_id, user_id)`: Lấy answers theo attempt, có kiểm tra owner nếu truyền user_id.
- `update(session, answer_id, answer_in)`: Cập nhật answer khi attempt chưa submit; nếu đổi option thì tính lại score/is_correct.

### 7.4. `AssessmentAttempt.py` - `AssessmentAttemptService`

- `_is_attempt_time_up(attempt)`: Kiểm tra attempt hết thời gian chưa.
- `start_attempt(session, project_id, user_id, assignment_id)`: Tạo attempt mới nếu user chưa có attempt active cho project.
- `save_attempt(session, attempt_id, question_id, user_id, score)`: Lưu hoặc cập nhật answer trong attempt đang làm.
- `submit_attempt(session, attempt_id, user_id)`: Đánh dấu attempt submitted và gọi `AssessmentResultService.create_from_attempt`.

### 7.5. `assessment_Result.py` - `AssessmentResultService`

- `__init__(session)`: Lưu session.
- `_calculate_readiness(total_score)`: Trên 80 là `high`, từ 50 là `medium`, dưới 50 là `low`.
- `_calculate_weighted_score(answers)`: Tính điểm phần trăm có trọng số theo `Criteria.weight`.
- `create_from_attempt(attempt_id)`: Tạo `AssessmentResults` từ answers; chống tạo duplicate quá gần; sau đó cố gắng gọi `AIAnalysisService.generate`.

### 7.6. `ai_analysis.py` - `AIAnalysisService`

- `__init__(session)`: Lưu session và khởi tạo `AIUsageService`.
- `_build_payload(result)`: Tạo analysis text, strengths, weaknesses, recommendations theo readiness level.
- `generate(result_id, model_name, tokens_used)`: Kiểm tra quota/rate limit, tạo hoặc update `AIAnalysis`, log usage.

### 7.7. `criteria.py` - `CriteriaService`

- `get_criteria(session, criteria_id, project_id)`: Lấy criteria theo id; `project_id` chỉ để tương thích API cũ vì criteria đang global.
- `list_criteria(session)`: Lấy toàn bộ criteria sort theo tên.

### 7.8. `quiz_templates.py`

- `build_vietnamese_quiz_questions(title, description, count)`: Hiện trả rỗng. Đây là chỗ giữ cho fallback/template cũ, nhưng luồng hiện tại ưu tiên sinh câu hỏi bằng AI từ source.

## 8. Service chấm code qua GitHub

### 8.1. `github_code_reader.py`

- `GithubFileContent`: Dataclass chứa `path` và `content` của một file code.
- `GithubCodeSnapshot`: Dataclass chứa repo url, owner, repo name, branch/ref, commit hash, files và combined content.
- `read_code_repo(github_repo_url, ref=None)`: Entry chính. Validate URL, lấy default branch/ref, lấy commit hash, tải zip, extract tạm, lọc file code, trả snapshot.
- `_parse_github_url(github_repo_url)`: Chỉ chấp nhận `github.com` hoặc `www.github.com`, parse owner/repo và validate ký tự.
- `_github_headers()`: Tạo header GitHub API; dùng `GITHUB_TOKEN` nếu có để tăng rate limit hoặc đọc repo private.
- `_get_repo_metadata(owner, repo_name)`: Gọi GitHub API lấy metadata; 404 nếu repo không tồn tại/private.
- `_get_latest_commit_hash(owner, repo, branch)`: Lấy sha commit của ref; lỗi thì trả `None` để không chặn luồng.
- `_download_repo_zip(owner, repo, branch)`: Tải zipball, chặn lỗi API và repo quá lớn theo `MAX_ZIP_BYTES`.
- `_safe_extract(zip_file, extract_to)`: Extract zip an toàn, chặn path traversal và tổng dung lượng extract quá lớn.
- `_find_extracted_root(extracted_dir)`: Tìm thư mục gốc sau khi giải nén zip GitHub.
- `_should_ignore(path)`: Bỏ qua `.git`, `.github`, `node_modules`, `venv`, `dist`, `build`, ...
- `_collect_code_files(repo_root)`: Lọc file theo extension code, giới hạn số file, size mỗi file và tổng ký tự.
- `_combine_files(files)`: Ghép các file thành một text, mỗi file có marker `// File: path`.

### 8.2. `code_submissions.py` - `CodeSubmissionService`

- `__init__(session)`: Lưu session và khởi tạo `UserSubscriptionService`.
- `_set_if_present(model_obj, field_name, value)`: Set field nếu model có, giúp tương thích migration.
- `_estimate_feedback_tokens(_)`: Trả token completion cố định cho code review.
- `_resolve_project_id(submission)`: Lấy project id qua assignment của submission.
- `submit_code(user_id, assignment_id, github_repo_url, file_path, commit_hash)`: Kiểm tra subscription, assignment, tạo submission; nếu có GitHub URL thì tự động trigger AI grading.
- `_trigger_ai_grading(submission_id)`: Luồng chấm chính: đọc repo GitHub, lưu commit hash, build prompt tiếng Việt, gọi `AITransactionService.chat`, parse response, lưu feedback, cập nhật score/status.
- `get_best_score(user_id, assignment_id)`: Lấy điểm cao nhất của user trong assignment.
- `get_submission_history(user_id, assignment_id)`: Lấy lịch sử nộp code.
- `get_submission_detail(submission_id)`: Trả submission kèm feedback nếu có.
- `_extract_github_info(content)`: Lấy JSON từ response AI, bỏ code fence nếu AI trả markdown.
- `_parse_github_response(content)`: Parse JSON AI; fallback thành overview nếu JSON lỗi; tương thích key cũ `Code_quality_score`.
- `_to_float_or_none(value)`: Ép score về float và clamp trong 0-10.
- `_string_or_none(value)`: Chuẩn hóa list/dict/string thành string hoặc `None`.
- `_build_code_review_prompt(assignment, repo_url, branch, commit_hash, combined_content)`: Tạo prompt tiếng Việt yêu cầu AI đánh giá overview, flow, score, strengths, weaknesses, improvement suggestions.

### 8.3. `Ai_code_feedback.py` - `AICodeFeedbackService`

- `__init__()`: Khởi tạo `AIUsageService`.
- `_set_if_present(model_obj, field_name, value)`: Set field tương thích schema.
- `_estimate_tokens(*parts)`: Ước lượng token từ độ dài feedback.
- `_resolve_project_id(session, submission)`: Lấy project id từ assignment.
- `create(session, submission_id, overview, flow_analysis, improvement_suggestions, generated_by, code_quality_score, logic_score, performance_score, strengths, weaknesses, model_name, tokens_used, track_usage)`: Tạo feedback nếu chưa tồn tại; có thể check quota/rate limit và log usage; cập nhật score trung bình, status `graded`, `graded_at`.
- `get_by_submission(session, submission_id)`: Lấy feedback theo submission.
- `update(session, feedback_id, ...)`: Cập nhật feedback và nếu đủ 3 score thì cập nhật lại score submission.
- `delete(session, feedback_id)`: Xóa feedback.
- `admin_stats(session)`: Tổng feedback và điểm trung bình quality/logic/performance.

## 9. Service nguồn AI-generated

### `ai_Generated_Source.py` - `AIGeneratedSourceService`

- `create(session, project_id, source_url, title, content_summary, source_type)`: Tạo source AI-generated cho project.
- `get_by_project(session, project_id)`: Lấy source theo project.
- `get_by_id(session, source_id)`: Lấy một source hoặc 404.
- `update(session, source_id, source_url, title, content_summary, source_type)`: Cập nhật các field được truyền.
- `delete(session, source_id)`: Xóa source.
- `search(session, project_id, keyword)`: Tìm theo title hoặc content summary.
- `stats(session, project_id)`: Đếm tổng source và group theo `source_type`.

## 10. Service bài tập, order, payment, admin

### 10.1. `assignment.py` - `AssignmentService`

- `_set_if_present(model_obj, field_name, value)`: Set field nếu schema có.
- `get_assigment(project_id, session)`: Alias typo cũ, gọi `get_assignments`.
- `get_assignments(project_id, session)`: Lấy assignments của project, sort mới nhất trước.
- `create_assignment(session, project_id, title, description, difficulty_level, assignment_type, generated_by, max_score, is_active, due_date)`: Tạo assignment; hỗ trợ các field mở rộng nếu model có.

### 10.2. `order.py` - `OrderService`

- `__init__(session)`: Lưu session.
- `create_order(user_id, plan_id, order_code, plan_name, amount, currency, payment_method)`: Tạo order pending/unpaid; nếu user đã có pending order cùng plan thì trả error và order cũ.
- `get_order(user_id, status, payment_status, payment_method, skip, limit)`: Lọc order theo user/trạng thái/phương thức thanh toán, trả danh sách và total.

Lưu ý phản biện/kỹ thuật: file này import `Order` và `PaymentTransaction`; cần đảm bảo model thực tế có các class đó trong `app.models.models`. Nếu DB/model hiện chỉ có `OrderBase` hoặc `PaymentTransactions`, phần này cần đồng bộ lại trước khi dùng production.

### 10.3. `momo_payment.py` - `MomoPaymentService`

- `__init__(session)`: Lưu session.
- `_sign(raw_signature)`: Tạo HMAC SHA256 bằng `MOMO_SECRET_KEY`.
- `_require_momo_config()`: Kiểm tra partner code, access key, secret key, endpoint, redirect URL, IPN URL; chặn placeholder.
- `_serialize_transaction(transaction, user, plan)`: Chuẩn hóa transaction thành dict trả frontend/admin.
- `_safe_int(value)`: Ép int an toàn.
- `create_payment(user_id, plan_id)`: Tạo MoMo payment. Nếu plan miễn phí thì subscribe ngay; nếu có phí thì tạo `PaymentTransactions`, ký request, gọi endpoint MoMo, lưu payUrl/deeplink/qr.
- `create_card_payment(user_id, plan_id)`: Luồng card giả/lập tức paid; tạo transaction paid và subscribe plan.
- `_build_ipn_signature(data)`: Tạo chữ ký kỳ vọng cho IPN.
- `handle_ipn(data)`: Verify chữ ký MoMo; tìm transaction; nếu resultCode 0 và amount khớp thì set paid và subscribe plan; nếu không thì ghi failed.
- `get_status(user_id, order_id)`: Lấy trạng thái transaction của user.
- `list_transactions(status, user_id, skip, limit)`: Admin/user listing transaction có phân trang và filter.

### 10.4. `admin_stats.py` - `AdminStatsService`

- `__init__(session)`: Lưu session.
- `_safe_year(year)`: Giới hạn year trong khoảng hợp lý từ 2000 đến năm hiện tại + 1.
- `_count_users()`: Đếm tổng user, active user, admin user.
- `_user_registrations_by_month(year)`: Thống kê user đăng ký theo 12 tháng.
- `_subscription_updates_by_quarter(year)`: Thống kê subscription được tạo theo quý.
- `_subscription_updates_by_plan(year)`: Đếm subscription theo từng plan trong năm.
- `_active_subscriptions_by_plan()`: Đếm subscription đang active theo plan.
- `dashboard(year)`: Tổng hợp dữ liệu dashboard admin: totals, đăng ký user theo tháng, update subscription theo quý, theo plan và active plan.

## 11. Điểm mạnh để nói khi phản biện

- **Tách tầng rõ ràng**: Route chỉ điều phối HTTP, service xử lý nghiệp vụ.
- **Có kiểm tra quyền và dữ liệu**: Project kiểm tra owner/access; subscription kiểm tra plan; quiz kiểm tra câu hỏi/option hợp lệ.
- **Có kiểm soát AI usage**: `AITransactionService` và `AIUsageService` lưu token, model, action type và kiểm tra limit tháng.
- **AI provider linh hoạt**: Dùng OpenAI-compatible client nên Groq/Cerebras dùng chung một interface.
- **Giảm hallucination khi sinh câu hỏi**: Câu hỏi AI phải có `source_quote` nằm trong tài liệu gốc.
- **Xử lý file đa dạng**: TXT/PDF/DOCX/PPTX/image/web, có fallback OCR cho PDF scan.
- **Chấm code an toàn hơn**: GitHub URL được validate, zip extract chống path traversal, có giới hạn dung lượng/file/ký tự.
- **Tối ưu thời gian generate bài học**: Curriculum chỉ generate preview trước, các module sau generate khi cần hoặc prefetch nền.

## 12. Điểm cần lưu ý/có thể bị hỏi

- Một số hàm giữ tên typo hoặc compatibility như `get_assigment`, `generate_lessions`, `generate_lession_content`, `call_lln`; nên giải thích là giữ tương thích API cũ.
- `order.py` cần kiểm tra lại đồng bộ model `Order`/`PaymentTransaction` nếu phần order được demo.
- Một số prompt trong `ai_service.py` còn không dấu/tiếng Anh ở system prompt cũ; luồng GitHub code review mới đã chuyển prompt người dùng sang tiếng Việt.
- Các service dùng `datetime.utcnow()`; nếu triển khai lớn nên cân nhắc timezone-aware datetime.
- Các hàm `_build_module_questions` và `build_vietnamese_quiz_questions` hiện là extension point trả rỗng, vì hệ thống đã chuyển sang sinh câu hỏi từ source bằng AI.
- Với OCR PDF scan cần cài Tesseract và Poppler, nếu thiếu thì chỉ extract được PDF có text layer.
