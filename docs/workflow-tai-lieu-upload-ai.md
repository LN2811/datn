# Workflow 1: Người dùng gửi tài liệu và AI sử dụng tài liệu

## 1. Mục tiêu chức năng

Chức năng này cho phép người dùng đưa tài liệu học tập vào một project. Tài liệu có thể là file upload hoặc link ngoài. Sau khi nhận tài liệu, backend lưu file vật lý, lưu metadata vào database, trích xuất text, làm sạch text, chia nhỏ thành các đoạn `MaterialChunk`, sau đó các chức năng sinh bài học và sinh câu hỏi sẽ lấy dữ liệu này để gọi AI.

Điểm cần nói khi phản biện:

> File gốc không được lưu trực tiếp vào database. Backend lưu file trong thư mục storage của server, còn database chỉ lưu đường dẫn file và thông tin metadata. Nội dung văn bản sau khi đọc từ file được chia nhỏ và lưu vào bảng `material_chunks` để các service AI sử dụng lại.

## 2. Endpoint chính

File route:

```text
backend/app/api/route/LearningMaterials.py
```

Các endpoint chính:

| Chức năng | Method | Endpoint | Route function | Service |
|---|---:|---|---|---|
| Upload/tạo tài liệu | POST | `/learning-materials/project/{project_id}/materials` | `create_material` | `LearningMaterialService.create_material` |
| Lấy danh sách tài liệu theo project | GET | `/learning-materials/project/{project_id}` | `get_materials_by_project` | `LearningMaterialService.get_materials_by_project` |
| Lấy chi tiết tài liệu | GET | `/learning-materials/{material_id}` | `get_material_detail` | `LearningMaterialService.get_material_detail` |
| Cập nhật tài liệu | PATCH | `/learning-materials/{material_id}` | `update_material` | `LearningMaterialService.update_material` |
| Xóa tài liệu | DELETE | `/learning-materials/{material_id}` | `delete_material` | `LearningMaterialService.delete_material` |

Router được gắn vào app tại:

```text
backend/app/api/main.py
```

```python
api_router.include_router(
    LearningMaterials.router,
    prefix="/learning-materials",
    tags=["learning-materials"],
)
```

## 3. Flow tổng quát

```text
Người dùng chọn file hoặc nhập external_link
  -> Frontend gửi request multipart/form-data
  -> POST /learning-materials/project/{project_id}/materials
  -> Authen.get_current_user lấy user hiện tại
  -> LearningMaterials.create_material
  -> LearningMaterialService.create_material
  -> kiểm tra project tồn tại
  -> kiểm tra chỉ được gửi file hoặc link, không gửi cả hai
  -> nếu là file: save_uploaded_file
  -> tạo bản ghi LearningMaterials
  -> commit DB
  -> MaterialChunkService.save_material_chunk
  -> extract_text đọc nội dung file/link
  -> clean_learning_material_text làm sạch text
  -> _split_passages chia text thành đoạn nhỏ
  -> lưu từng đoạn vào bảng material_chunks
  -> các service sinh curriculum/quiz lấy lại text để gọi AI
```

## 4. Người dùng gửi gì lên backend

Request upload tài liệu thường gồm:

```text
project_id: uuid trên URL
title: tên tài liệu
file_path: UploadFile hoặc null
external_link: link ngoài hoặc null
```

Quy tắc validate trong `LearningMaterialService.create_material`:

- Project phải tồn tại.
- Không được vừa gửi `file_path` vừa gửi `external_link`.
- Bắt buộc có một trong hai: file upload hoặc external link.

Nếu sai thì backend trả lỗi `400`.

## 5. Service nhận và xử lý tài liệu

File service:

```text
backend/app/services/LearningMaterials.py
```

Hàm chính:

```python
LearningMaterialService.create_material(...)
```

Luồng xử lý:

1. Query project:

```python
project = self.session.get(Projects, project_id)
```

2. Nếu không có project:

```text
404 Project not found
```

3. Validate file/link.

4. Nếu có file upload thì gọi:

```python
file_info = save_uploaded_file(file_path)
saved_file_path = file_info["file_path"]
```

5. Tạo metadata:

```python
material = LearningMaterials(
    project_id=project_id,
    title=title,
    file_path=saved_file_path,
    external_link=external_link,
    uploaded_by=current_user.id,
)
```

6. Lưu DB:

```python
self.session.add(material)
self.session.commit()
self.session.refresh(material)
```

7. Gọi service chia chunk:

```python
MaterialChunkService(self.session).save_material_chunk(
    material_id=material.id,
)
```

Lưu ý kỹ thuật:

- Việc tạo chunk được đặt trong `try/except`.
- Nếu chunk lỗi, backend log warning nhưng vẫn trả về material đã upload.
- Điều này giúp upload không bị mất nếu OCR/parser gặp lỗi, nhưng khi sinh câu hỏi có thể thiếu dữ liệu chunk.

## 6. File được lưu ở đâu và lưu như thế nào

File lưu bằng service:

```text
backend/app/services/storage.py
```

Hàm:

```python
save_uploaded_file(upload_file: UploadFile)
```

Thư mục lưu:

```python
upload_dir = Path(__file__).resolve().parents[1] / "storage"
```

Tức là file vật lý nằm trong:

```text
backend/app/storage/
```

Cách đặt tên file:

```python
filename = f"{uuid.uuid4()}{ext}"
file_path = upload_dir / filename
```

Ví dụ:

```text
backend/app/storage/6b4c9f2f-0d37-4b51-a9e1-3a9fd30d6f48.pdf
```

Các extension được phép:

```text
.pdf, .docx, .pptx, .txt, .jpg, .jpeg, .png
```

Nếu file khác loại:

```text
400 File type not allowed
```

Kết quả trả về:

```python
{
    "file_path": str(file_path),
    "filename": filename,
}
```

Điểm phản biện:

> Hệ thống đổi tên file bằng UUID để tránh trùng tên giữa nhiều người dùng. Hai người upload cùng một file thì vẫn sinh ra hai file vật lý khác nhau và hai bản ghi `LearningMaterials` khác nhau.

## 7. Metadata được lưu vào database như thế nào

Model:

```text
backend/app/models/models.py
```

```python
class LearningMaterials(BaseModel, table=True):
    __tablename__ = "learning_materials"
```

Các cột quan trọng:

| Cột | Ý nghĩa |
|---|---|
| `id` | ID tài liệu |
| `project_id` | Tài liệu thuộc project nào |
| `uploaded_by` | User upload tài liệu |
| `title` | Tên tài liệu |
| `file_path` | Đường dẫn file vật lý nếu upload file |
| `external_link` | Link ngoài nếu người dùng nhập link |
| `created_at` | Thời điểm tạo |

Database không lưu binary file. Database chỉ lưu metadata và đường dẫn.

## 8. Sau khi lưu DB thì tài liệu được chia nhỏ như thế nào

File service:

```text
backend/app/services/material_chunk.py
```

Hàm:

```python
MaterialChunkService.save_material_chunk(material_id=...)
```

Luồng chi tiết:

1. Query material:

```python
material = self.session.get(LearningMaterials, material_id)
```

2. Nếu material không tồn tại:

```text
404 Learning material not found
```

3. Kiểm tra material đã có chunk chưa:

```python
existing = self.session.exec(
    select(MaterialChunk).where(MaterialChunk.material_id == material_id)
).all()
```

Nếu đã có chunk thì return luôn, không tạo trùng.

4. Xác định nguồn đọc:

```python
source = material.file_path or material.external_link
```

5. Đọc text:

```python
text = extract_text(source)
```

6. Làm sạch:

```python
text = clean_learning_material_text(text)
```

7. Chia đoạn:

```python
chunks = _split_passages(text)
```

8. Lưu từng chunk:

```python
MaterialChunk(
    material_id=material_id,
    content=chunk,
    chunk_index=index,
)
```

## 9. Chunk được lưu vào bảng nào

Model:

```python
class MaterialChunk(SQLModel, table=True):
    __tablename__ = "material_chunks"
```

Các cột:

| Cột | Ý nghĩa |
|---|---|
| `id` | ID chunk |
| `material_id` | Chunk thuộc tài liệu nào |
| `curriculum_module_id` | Nếu chunk gắn với module |
| `content` | Nội dung đoạn text |
| `chunk_index` | Thứ tự đoạn trong tài liệu |
| `created_at` | Thời điểm tạo |

Điểm phản biện:

> Chunk giúp hệ thống không phải đẩy toàn bộ file dài vào AI một lần. Khi sinh câu hỏi, hệ thống lấy các chunk đã lưu theo thứ tự để tạo nguồn dữ liệu.

## 10. Hàm nào đọc text từ file hoặc link

File:

```text
backend/app/services/file_parser.py
```

Hàm entry:

```python
extract_text(path_or_url: str)
```

Các loại nguồn được xử lý:

| Nguồn | Cách đọc |
|---|---|
| URL `http/https` | `_extract_text_from_web`, dùng `requests` và `BeautifulSoup` |
| `.txt` | Đọc file text UTF-8 |
| `.pdf` có text layer | `_extract_text_from_pdf_layer` bằng `PyPDF2` |
| `.pdf` fallback | `extract_text_pdf` bằng `pdfplumber` |
| PDF scan | `extract_text_with_ocr` bằng `pdf2image` + `pytesseract` |
| `.docx` | Đọc XML trong zip, prefix `word/` |
| `.pptx` | Đọc XML trong zip, prefix `ppt/slides/` |
| `.jpg/.jpeg/.png` | OCR bằng `pytesseract` |

Các cấu hình OCR liên quan nằm trong:

```text
backend/app/core/config.py
```

```python
TESSERACT_CMD
POPPLER_PATH
OCR_LANGS = "vie+eng"
OCR_PDF_DPI = 200
```

Lưu ý: trong code là `POPPLER_PATH`.

## 11. Hàm nào làm sạch text

Các hàm chính:

```text
backend/app/services/text_cleaner.py
backend/app/services/ai_service.py
```

Luồng:

```python
extract_text(...)
  -> clean_vietnamese_text(...)

MaterialChunkService.save_material_chunk(...)
  -> clean_learning_material_text(...)
  -> _split_passages(...)
```

`clean_vietnamese_text` chịu trách nhiệm normalize text tiếng Việt. `clean_learning_material_text` là lớp làm sạch riêng cho tài liệu học tập trước khi chia chunk hoặc đưa vào AI.

## 12. AI lấy tài liệu từ DB như thế nào để sinh câu hỏi

File:

```text
backend/app/services/questions.py
```

Hàm lấy nguồn:

```python
QuestionService._collect_assignment_source_text(...)
```

Luồng:

```text
Assignment
  -> assignment.project
  -> project.materials
  -> query MaterialChunk theo từng material.id
  -> order_by(MaterialChunk.chunk_index)
  -> join content các chunk
  -> _limit_source_text
  -> đưa vào prompt sinh câu hỏi
  -> AITransactionService.chat
```

Code chính:

```python
chunks = session.exec(
    select(MaterialChunk)
    .where(MaterialChunk.material_id == material.id)
    .order_by(MaterialChunk.chunk_index)
).all()
```

Điểm phản biện:

> Sinh quiz ưu tiên lấy dữ liệu từ bảng `material_chunks`, không đọc lại toàn bộ file gốc nếu chunk đã được tạo.

## 13. AI lấy tài liệu như thế nào để sinh curriculum/bài học

File:

```text
backend/app/services/curriculum_generate.py
```

Hàm lấy nguồn:

```python
CurriculumGenerationService._collect_project_material_text(...)
```

Luồng:

```text
project_id
  -> query LearningMaterials theo project_id
  -> với từng material lấy file_path hoặc external_link
  -> extract_text(source)
  -> clean_learning_material_text
  -> ghép title + extracted_text
  -> full_text
  -> tạo outline/bài học
  -> AITransactionService.chat
```

Khác với sinh quiz, luồng curriculum hiện đang đọc lại từ `LearningMaterials.file_path` hoặc `external_link`, sau đó extract text lại. Nếu muốn tối ưu, có thể sửa để ưu tiên dùng `MaterialChunk` giống quiz.

## 14. Những service tham gia theo chức năng

| Service/hàm | Vai trò |
|---|---|
| `LearningMaterialService.create_material` | Nhận yêu cầu tạo tài liệu, validate, lưu metadata |
| `save_uploaded_file` | Lưu file vật lý vào `backend/app/storage` |
| `MaterialChunkService.save_material_chunk` | Đọc nội dung và chia tài liệu thành chunk |
| `extract_text` | Trích xuất text từ PDF, DOCX, PPTX, TXT, ảnh hoặc web |
| `clean_vietnamese_text` | Chuẩn hóa text tiếng Việt |
| `clean_learning_material_text` | Làm sạch text tài liệu học tập |
| `_split_passages` | Chia text thành các đoạn nhỏ |
| `QuestionService._collect_assignment_source_text` | Lấy chunk để sinh câu hỏi |
| `CurriculumGenerationService._collect_project_material_text` | Lấy tài liệu để sinh curriculum |
| `AITransactionService.chat` | Gọi AI và log usage |

## 15. Nếu hai người dùng cùng upload một file giống nhau

Kết quả lưu trữ:

- Mỗi lần upload sinh filename UUID khác nhau.
- Mỗi người có một bản ghi `LearningMaterials` riêng.
- Mỗi tài liệu có bộ `MaterialChunk` riêng.
- Nếu nội dung file giống nhau thì text/chunk có thể giống nhau, nhưng không dùng chung dữ liệu ở DB.

Kết quả AI:

- Nếu cùng tài liệu, cùng prompt, cùng model, cùng số câu hỏi thì câu hỏi có thể giống hoặc gần giống.
- Nhưng hệ thống không cache kết quả theo file hash.
- AI có tính sinh tự nhiên, nên hai lần gọi vẫn có thể khác nhau.
- Nếu muốn đảm bảo khác nhau hơn, có thể tăng variation trong prompt hoặc thêm seed/context theo user.

## 16. Câu trả lời ngắn khi phản biện

**File upload lưu ở đâu?**

File nằm trong `backend/app/storage/`, tên file được đổi thành UUID để tránh trùng.

**DB lưu gì?**

DB lưu metadata trong `learning_materials`: title, project_id, uploaded_by, file_path hoặc external_link.

**Nội dung text lưu ở đâu?**

Text sau khi đọc và chia nhỏ lưu trong `material_chunks`.

**Hàm nào lưu file?**

`save_uploaded_file` trong `backend/app/services/storage.py`.

**Hàm nào chia tài liệu?**

`MaterialChunkService.save_material_chunk`.

**AI lấy tài liệu bằng cách nào?**

Sinh quiz lấy từ `MaterialChunk`. Sinh curriculum hiện lấy từ `LearningMaterials` rồi extract text lại từ `file_path` hoặc `external_link`.
