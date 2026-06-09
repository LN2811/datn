import unittest
import uuid
from types import SimpleNamespace

from app.core.config import settings
from app.services.material_chunk import MaterialChunkService
from app.services.ai_service import (
    analyze_extracted_text_quality,
    _split_passages,
    calculate_expected_module_count,
    clean_extracted_text,
    deduplicate_passages,
    generate_curriculum_outline_fallback,
    is_extracted_text_quality_acceptable,
)
from app.services.questions import QuestionService


class LearningMaterialPipelineTests(unittest.TestCase):
    def test_clean_extracted_text_repairs_common_spacing_and_deduplicates_blocks(self):
        repeated = "Noi dung lap lai can duoc loai bo khoi tai lieu hoc tap."
        cleaned = clean_extracted_text(
            "\n\n".join(
                [
                    "H TML va CS S duoc dung tr ong tem plate.",
                    repeated,
                    repeated,
                ]
            )
        )

        self.assertIn("HTML va CSS duoc dung trong template.", cleaned)
        self.assertEqual(cleaned.count(repeated), 1)

    def test_clean_extracted_text_preserves_code_lines(self):
        code = """```html
<div class="card">
  <span>Hello</span>
</div>
```"""

        self.assertIn(code, clean_extracted_text(f"Vi du HTML:\n\n{code}"))

    def test_quality_gate_rejects_weak_text(self):
        self.assertFalse(is_extracted_text_quality_acceptable("a b c"))

    def test_module_count_scales_with_document_length(self):
        self.assertGreaterEqual(calculate_expected_module_count("noi dung " * 400), 3)
        self.assertGreater(
            calculate_expected_module_count("noi dung " * 8_000),
            10,
        )

    def test_outline_fallback_uses_multiple_modules(self):
        outline = generate_curriculum_outline_fallback(
            " ".join(f"Noi dung bai hoc thu {index}." for index in range(300))
        )

        self.assertGreaterEqual(len(outline["modules"]), 3)

    def test_quiz_context_samples_later_passages(self):
        source = "\n\n".join(
            f"Doan {index} " + ("noi dung " * 80)
            for index in range(12)
        )

        limited = QuestionService._limit_source_text(source)

        self.assertIn("Doan 0", limited)
        self.assertIn("Doan 11", limited)

    def test_clean_extracted_text_removes_repeated_page_artifacts_before_merging(self):
        cleaned = clean_extracted_text(
            "\n".join(
                [
                    "Giao trinh lap trinh tong quat",
                    "Chương   1 - Nhap mon",
                    "Noi dung dau tien bi ngat",
                    "sang dong tiep theo.",
                    "12",
                    "Giao trinh lap trinh tong quat",
                    "Giao trinh lap trinh tong quat",
                    "Giao trinh lap trinh tong quat",
                ]
            )
        )

        self.assertNotIn("Giao trinh lap trinh tong quat", cleaned)
        self.assertNotIn("\n12\n", f"\n{cleaned}\n")
        self.assertIn("Chương 1: Nhap mon", cleaned)
        self.assertIn("Noi dung dau tien bi ngat sang dong tiep theo.", cleaned)

    def test_quality_report_exposes_dirty_metrics(self):
        dirty_text = "\n".join(
            ["Giao trinh lap lai"] * 20
            + ["n ộ i   d u n g ,  b ị   v ỡ   c h ữ"] * 20
        )

        report = analyze_extracted_text_quality(dirty_text)

        self.assertGreater(report.dirty_score, 0)
        self.assertGreater(report.repeated_ratio, 0)
        self.assertGreater(report.abnormal_spacing_ratio, 0)
        self.assertGreater(report.extracted_chars, report.final_chars)
        self.assertGreater(report.dirty_score, settings.EXTRACTED_TEXT_MAX_DIRTY_SCORE)
        self.assertFalse(
            is_extracted_text_quality_acceptable(
                dirty_text,
                quality_report=report,
            )
        )

    def test_deduplicate_passages_removes_exact_and_near_duplicates(self):
        base = (
            "Noi dung chuong nay trinh bay kien thuc tong quat va vi du "
            "de nguoi hoc co the ap dung vao bai tap thuc hanh."
        )
        passages, duplicate_count, duplicate_chars = deduplicate_passages(
            [
                base,
                base,
                base.replace("thuc hanh", "thuc te"),
                "Noi dung rieng biet cua chuong tiep theo.",
            ]
        )

        self.assertEqual(len(passages), 2)
        self.assertEqual(duplicate_count, 2)
        self.assertGreater(duplicate_chars, 0)

    def test_long_dirty_pdf_like_fixture_produces_deduplicated_clean_chunks(self):
        footer = "Giao trinh tong quat - Khoa Cong nghe thong tin"
        repeated_paragraph = (
            "Noi dung lap lai o cuoi trang can duoc loai bo truoc khi luu chunk. "
            "Doan van nay dai de mo phong noi dung giao trinh bi lap khi extract PDF."
        )
        pages = []
        for index in range(1, 90):
            pages.append(
                "\n".join(
                    [
                        footer,
                        f"Chương   {index} - Noi dung chuong",
                        f"{index}",
                        "Kien thuc cua chuong duoc trinh bay theo tung muc.",
                        "Dong van bi ngat",
                        "sang trang tiep theo.",
                        repeated_paragraph,
                        repeated_paragraph,
                        footer,
                    ]
                )
            )
        raw_text = "\n\n".join(pages)

        cleaned = clean_extracted_text(raw_text)
        report = analyze_extracted_text_quality(raw_text, cleaned_text=cleaned)
        chunks, duplicate_count, _ = deduplicate_passages(_split_passages(cleaned))

        self.assertNotIn(footer, cleaned)
        self.assertTrue(chunks)
        self.assertGreater(report.duplicate_removed_chars + duplicate_count, 0)
        self.assertLessEqual(cleaned.count(repeated_paragraph), 1)
        self.assertEqual(len(chunks), len(set(chunks)))
        self.assertTrue(
            all("  " not in chunk and footer not in chunk for chunk in chunks)
        )

    def test_save_material_chunk_does_not_insert_duplicate_chunks(self):
        class EmptyResult:
            @staticmethod
            def all():
                return []

        class FakeSession:
            def __init__(self):
                self.added = []

            @staticmethod
            def get(_model, _material_id):
                return SimpleNamespace(id=_material_id)

            @staticmethod
            def exec(_statement):
                return EmptyResult()

            def add(self, item):
                self.added.append(item)

            @staticmethod
            def commit():
                return None

            @staticmethod
            def refresh(_item):
                return None

        repeated = (
            "Noi dung chuong trinh bay kien thuc tong quat va vi du thuc hanh "
            "de nguoi hoc ap dung vao bai tap."
        )
        unique = (
            "Phan tiep theo mo ta quy trinh xu ly du lieu voi nhieu buoc kiem tra "
            "va danh gia ket qua."
        )
        session = FakeSession()

        chunks = MaterialChunkService(session).save_material_chunk(
            material_id=uuid.uuid4(),
            text="\n\n".join([repeated, repeated, unique]),
        )

        self.assertEqual(len(chunks), 2)
        self.assertEqual(len({chunk.content for chunk in chunks}), 2)


if __name__ == "__main__":
    unittest.main()
