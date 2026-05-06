import logging
import uuid

from fastapi import HTTPException
from sqlmodel import Session, select

from app.core.db import engine
from app.models.models import (
    Assignments,
    Criteria,
    CurriculumModules,
    Curriculums,
    LearningMaterials,
    Projects,
    QuestionOptions,
    Questions,
)
from app.services.ai_service import (
    build_module_source_description,
    clean_learning_material_text,
    extract_curriculum_outline_from_toc,
    generate_curriculum_outline_fallback,
    generate_lesson_content_from_source,
    generate_lesson_content_fallback,
)
from app.services.file_parser import extract_text
from app.services.quiz_templates import (
    QUESTIONS_PER_QUIZ,
    build_vietnamese_quiz_questions,
)
from app.services.text_cleaner import clean_vietnamese_text, has_vietnamese_mark

logger = logging.getLogger("uvicorn.error")


class CurriculumGenerationService:
    def _get_latest_curriculum(
        self,
        *,
        session: Session,
        project_id: uuid.UUID,
    ) -> Curriculums | None:
        return session.exec(
            select(Curriculums)
            .where(Curriculums.project_id == project_id)
            .order_by(Curriculums.created_at.desc())
        ).first()

    def _get_curriculum_modules(
        self,
        *,
        session: Session,
        curriculum_id: uuid.UUID,
    ) -> list[CurriculumModules]:
        return session.exec(
            select(CurriculumModules)
            .where(CurriculumModules.curriculum_id == curriculum_id)
            .order_by(CurriculumModules.order_index, CurriculumModules.created_at)
        ).all()

    def _has_newer_materials(
        self,
        *,
        session: Session,
        project_id: uuid.UUID,
        curriculum: Curriculums,
    ) -> bool:
        latest_material = session.exec(
            select(LearningMaterials)
            .where(LearningMaterials.project_id == project_id)
            .order_by(LearningMaterials.created_at.desc())
        ).first()
        if not latest_material:
            return False
        return latest_material.created_at > curriculum.created_at

    def _sync_curriculum_progress(
        self,
        *,
        session: Session,
        curriculum: Curriculums,
        modules: list[CurriculumModules],
    ) -> Curriculums:
        total_module = len(modules)
        ready_module = sum(
            1
            for module in modules
            if module.generate_status == "ready" and bool(module.content)
        )

        if (
            curriculum.total_module == total_module
            and curriculum.ready_module == ready_module
        ):
            return curriculum

        curriculum.total_module = total_module
        curriculum.ready_module = ready_module
        session.add(curriculum)
        session.commit()
        session.refresh(curriculum)
        return curriculum

    def _get_project_or_404(
        self,
        *,
        session: Session,
        project_id: uuid.UUID,
    ) -> Projects:
        project = session.get(Projects, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return project

    def _collect_project_material_text(
        self,
        *,
        session: Session,
        project_id: uuid.UUID,
    ) -> str:
        materials = session.exec(
            select(LearningMaterials)
            .where(LearningMaterials.project_id == project_id)
            .order_by(LearningMaterials.created_at)
        ).all()

        if not materials:
            raise HTTPException(
                status_code=404,
                detail="No learning materials found for this project",
            )

        contents: list[str] = []
        for material in materials:
            source = material.file_path or material.external_link
            if not source:
                continue

            try:
                extracted_text = clean_learning_material_text(extract_text(source)).strip()
            except Exception as exc:
                logger.warning(
                    "Failed to extract learning material content. project_id=%s material_id=%s source=%s error_type=%s error=%s",
                    project_id,
                    material.id,
                    source,
                    type(exc).__name__,
                    exc,
                )
                continue

            if not extracted_text:
                logger.warning(
                    "No text extracted from learning material. project_id=%s material_id=%s source=%s",
                    project_id,
                    material.id,
                    source,
                )
                continue

            contents.append(f"{material.title}\n{extracted_text}")

        full_text = "\n\n".join(contents)
        if not full_text.strip():
            raise HTTPException(
                status_code=400,
                detail=(
                    "No content extracted from learning materials. "
                    "For scanned PDFs, verify OCR dependencies such as Tesseract and Poppler."
                ),
            )

        return full_text

    def _get_module_context_or_404(
        self,
        *,
        session: Session,
        module_id: uuid.UUID,
    ) -> tuple[Curriculums, CurriculumModules]:
        module = session.get(CurriculumModules, module_id)
        if not module:
            raise HTTPException(status_code=404, detail="Module not found")

        curriculum = session.get(Curriculums, module.curriculum_id)
        if not curriculum:
            raise HTTPException(status_code=404, detail="Curriculum not found")

        return curriculum, module

    @staticmethod
    def _question_assignment_field_name() -> str:
        if hasattr(Questions, "assignment_id"):
            return "assignment_id"
        if hasattr(Questions, "assignments_id"):
            return "assignments_id"
        raise HTTPException(
            status_code=500,
            detail="Question model does not define assignment reference field",
        )

    @staticmethod
    def _question_assignment_field():
        if hasattr(Questions, "assignment_id"):
            return getattr(Questions, "assignment_id")
        if hasattr(Questions, "assignments_id"):
            return getattr(Questions, "assignments_id")
        raise HTTPException(
            status_code=500,
            detail="Question model does not define assignment reference field",
        )

    def _get_or_create_lesson_criteria(self, *, session: Session) -> Criteria:
        criteria = session.exec(
            select(Criteria).where(Criteria.name == "Lesson comprehension")
        ).first()
        if criteria:
            return criteria

        criteria = Criteria(
            name="Lesson comprehension",
            description="Đánh giá mức độ hiểu nội dung bài học được tạo từ tài liệu.",
            weight=1.0,
        )
        session.add(criteria)
        session.commit()
        session.refresh(criteria)
        return criteria

    def _get_or_create_question_assignment(
        self,
        *,
        session: Session,
        project_id: uuid.UUID,
        curriculum: Curriculums,
    ) -> Assignments:
        assignment_title = f"Bộ câu hỏi - {curriculum.title} ({curriculum.id.hex[:8]})"
        assignment = session.exec(
            select(Assignments).where(
                Assignments.project_id == project_id,
                Assignments.title == assignment_title,
            )
        ).first()
        if assignment:
            return assignment

        assignment = Assignments(
            project_id=project_id,
            title=assignment_title,
            description=(
                "Bộ câu hỏi được tạo đồng thời với các bài học AI "
                f"trong curriculum: {curriculum.title}."
            ),
        )
        session.add(assignment)
        session.commit()
        session.refresh(assignment)
        return assignment

    @staticmethod
    def _build_questions_for_module(module: CurriculumModules) -> list[dict]:
        title = clean_vietnamese_text(module.title).strip() if module.title else "bài học này"
        description = clean_vietnamese_text(module.description or "").strip()
        return build_vietnamese_quiz_questions(title=title, description=description)

    @staticmethod
    def _create_question_options(
        *,
        session: Session,
        question: Questions,
        options: list[dict],
    ) -> None:
        for index, option_data in enumerate(options):
            content = clean_vietnamese_text(
                str(option_data.get("content") or "")
            ).strip()
            if not content:
                continue

            session.add(
                QuestionOptions(
                    question_id=question.id,
                    content=content,
                    is_correct=bool(option_data.get("is_correct", False)),
                    order_index=index,
                )
            )

    def _ensure_question_set_for_modules(
        self,
        *,
        session: Session,
        project_id: uuid.UUID,
        curriculum: Curriculums,
        modules: list[CurriculumModules],
    ) -> dict:
        if not modules:
            return {
                "question_assignment_id": None,
                "questions_count": 0,
            }

        criteria = self._get_or_create_lesson_criteria(session=session)
        assignment = self._get_or_create_question_assignment(
            session=session,
            project_id=project_id,
            curriculum=curriculum,
        )
        assignment_field = self._question_assignment_field()
        assignment_field_name = self._question_assignment_field_name()

        existing_questions = session.exec(
            select(Questions).where(assignment_field == assignment.id)
        ).all()
        expected_count = max(len(modules), 1) * QUESTIONS_PER_QUIZ
        legacy_unaccented = (
            bool(existing_questions)
            and all(not has_vietnamese_mark(question.content or "") for question in existing_questions)
        )
        if len(existing_questions) >= expected_count and not legacy_unaccented:
            return {
                "question_assignment_id": str(assignment.id),
                "questions_count": len(existing_questions),
            }

        created_questions: list[Questions] = []
        for module in modules:
            for generated_question in self._build_questions_for_module(module):
                question_payload = {
                    "project_id": project_id,
                    "criteria_id": criteria.id,
                    "curriculum_module_id": module.id,
                    "content": clean_vietnamese_text(generated_question["content"]),
                    "question_type": "single_choice",
                    "explanation": clean_vietnamese_text(
                        generated_question.get("explanation") or ""
                    ) or None,
                    "generated_by": "ai",
                    assignment_field_name: assignment.id,
                }
                question = Questions(**question_payload)
                session.add(question)
                session.flush()
                self._create_question_options(
                    session=session,
                    question=question,
                    options=generated_question.get("options", []),
                )
                created_questions.append(question)

        session.commit()
        for question in created_questions:
            session.refresh(question)

        return {
            "question_assignment_id": str(assignment.id),
            "questions_count": len(created_questions),
        }

    def _create_pending_modules(
        self,
        *,
        session: Session,
        curriculum: Curriculums,
        modules: list[dict],
        preview_count: int,
    ) -> list[CurriculumModules]:
        created_modules: list[CurriculumModules] = []

        for index, module_data in enumerate(modules, start=1):
            if not isinstance(module_data, dict):
                continue

            title = clean_vietnamese_text(
                str(module_data.get("title") or f"Module {index}")
            ).strip() or f"Module {index}"
            description = clean_vietnamese_text(
                str(module_data.get("description") or "")
            ).strip()

            module = CurriculumModules(
                curriculum_id=curriculum.id,
                title=title,
                description=description or None,
                content=None,
                generate_status="pending",
                is_preview=index <= preview_count,
                order_index=index,
            )
            session.add(module)
            created_modules.append(module)

        if not created_modules:
            session.delete(curriculum)
            session.commit()
            raise HTTPException(
                status_code=500,
                detail="AI response did not produce any modules",
            )

        session.commit()
        for module in created_modules:
            session.refresh(module)

        curriculum.total_module = len(created_modules)
        session.add(curriculum)
        session.commit()
        session.refresh(curriculum)

        return created_modules

    def _enrich_module_descriptions_from_source(
        self,
        *,
        modules: list[dict],
        full_text: str,
    ) -> list[dict]:
        enriched_modules: list[dict] = []
        for module_data in modules:
            if not isinstance(module_data, dict):
                continue

            title = clean_vietnamese_text(str(module_data.get("title") or "")).strip()
            description = clean_vietnamese_text(
                str(module_data.get("description") or "")
            ).strip()
            if not title:
                enriched_modules.append(module_data)
                continue

            module_data = {
                **module_data,
                "title": title,
                "description": description or module_data.get("description"),
            }

            source_description = clean_vietnamese_text(
                build_module_source_description(
                    text=full_text,
                    module_title=title,
                    module_description=description,
                )
            )
            if source_description and source_description != description:
                module_data["description"] = (
                    f"{description}\n\n{source_description}"
                    if description
                    else source_description
                )
            enriched_modules.append(module_data)

        return enriched_modules

    def _generate_module_content(
        self,
        *,
        session: Session,
        curriculum: Curriculums,
        module: CurriculumModules,
        full_text: str,
        mark_preview: bool | None = None,
    ) -> CurriculumModules:
        if module.generate_status == "ready" and module.content:
            if mark_preview is not None and module.is_preview != mark_preview:
                module.is_preview = mark_preview
                session.add(module)
                session.commit()
                session.refresh(module)
            return module

        if module.generate_status == "generating":
            return module

        was_ready = module.generate_status == "ready" and bool(module.content)

        module.generate_status = "generating"
        if mark_preview is not None:
            module.is_preview = mark_preview
        session.add(module)
        session.commit()
        session.refresh(module)

        try:
            content = generate_lesson_content_from_source(
                text=full_text,
                curriculum_title=curriculum.title,
                overview=curriculum.overview or "",
                module_title=module.title,
                module_description=module.description or "",
            ).strip()
            if not content:
                raise RuntimeError("AI returned empty lesson content")
        except Exception as exc:
            logger.warning(
                "Source lesson extraction failed. Falling back to source-based lesson. curriculum_id=%s module_id=%s error_type=%s error=%s",
                curriculum.id,
                module.id,
                type(exc).__name__,
                exc,
            )
            try:
                content = generate_lesson_content_fallback(
                    text=full_text,
                    curriculum_title=curriculum.title,
                    overview=curriculum.overview or "",
                    module_title=module.title,
                    module_description=module.description or "",
                ).strip()
            except Exception as fallback_exc:
                module.generate_status = "failed"
                session.add(module)
                session.commit()
                session.refresh(module)
                raise RuntimeError(str(fallback_exc)) from fallback_exc

            if not content:
                module.generate_status = "failed"
                session.add(module)
                session.commit()
                session.refresh(module)
                raise RuntimeError(str(exc)) from exc

        module.content = clean_vietnamese_text(content).strip()
        module.generate_status = "ready"
        if mark_preview is not None:
            module.is_preview = mark_preview
        if not was_ready:
            curriculum.ready_module = (curriculum.ready_module or 0) + 1

        session.add(module)
        session.add(curriculum)
        session.commit()
        session.refresh(module)
        session.refresh(curriculum)

        return module

    def _ensure_preview_modules_ready(
        self,
        *,
        session: Session,
        curriculum: Curriculums,
        modules: list[CurriculumModules],
        project_id: uuid.UUID,
        preview_count: int,
    ) -> list[CurriculumModules]:
        preview_modules: list[CurriculumModules] = []
        preview_candidates = modules[:preview_count]
        needs_generation = any(
            not (module.generate_status == "ready" and module.content)
            for module in preview_candidates
        )
        full_text = ""
        if needs_generation and preview_candidates:
            full_text = self._collect_project_material_text(
                session=session,
                project_id=project_id,
            )

        for module in preview_candidates:
            try:
                if module.generate_status == "ready" and module.content:
                    preview_modules.append(
                        self._generate_module_content(
                            session=session,
                            curriculum=curriculum,
                            module=module,
                            full_text=full_text,
                            mark_preview=True,
                        )
                    )
                elif full_text:
                    preview_modules.append(
                        self._generate_module_content(
                            session=session,
                            curriculum=curriculum,
                            module=module,
                            full_text=full_text,
                            mark_preview=True,
                        )
                    )
                else:
                    module.is_preview = True
                    session.add(module)
                    session.commit()
                    session.refresh(module)
                    preview_modules.append(module)
            except Exception as exc:
                logger.warning(
                    "Preview lesson generation failed. curriculum_id=%s module_id=%s error_type=%s error=%s",
                    curriculum.id,
                    module.id,
                    type(exc).__name__,
                    exc,
                )
                session.refresh(module)
                preview_modules.append(module)

        return preview_modules

    def generate_from_curriculum(
        self,
        *,
        session: Session,
        project_id: uuid.UUID,
        preview_count: int = 2,
        force_regenerate: bool = False,
    ) -> dict:
        project = self._get_project_or_404(session=session, project_id=project_id)
        latest_curriculum = self._get_latest_curriculum(
            session=session,
            project_id=project_id,
        )
        if (
            latest_curriculum
            and not force_regenerate
            and not self._has_newer_materials(
            session=session,
            project_id=project_id,
            curriculum=latest_curriculum,
            )
        ):
            existing_modules = self._get_curriculum_modules(
                session=session,
                curriculum_id=latest_curriculum.id,
            )
            if existing_modules:
                self._sync_curriculum_progress(
                    session=session,
                    curriculum=latest_curriculum,
                    modules=existing_modules,
                )
                preview_modules = self._ensure_preview_modules_ready(
                    session=session,
                    curriculum=latest_curriculum,
                    modules=existing_modules,
                    project_id=project_id,
                    preview_count=preview_count,
                )
                question_meta = self._ensure_question_set_for_modules(
                    session=session,
                    project_id=project_id,
                    curriculum=latest_curriculum,
                    modules=existing_modules,
                )
                session.refresh(latest_curriculum)
                return {
                    "message": "Existing curriculum reused",
                    "curriculum_id": str(latest_curriculum.id),
                    "total_module": latest_curriculum.total_module,
                    "ready_module": latest_curriculum.ready_module,
                    **question_meta,
                    "modules": preview_modules,
                }

        full_text = self._collect_project_material_text(
            session=session,
            project_id=project_id,
        )

        generated_by = "toc"
        outline = extract_curriculum_outline_from_toc(full_text)
        if outline is None:
            generated_by = "source"
            try:
                outline = generate_curriculum_outline_fallback(full_text)
            except HTTPException:
                raise
            except Exception as exc:
                logger.warning(
                    "Source outline generation failed. project_id=%s error_type=%s error=%s",
                    project_id,
                    type(exc).__name__,
                    exc,
                )
                raise HTTPException(
                    status_code=400,
                    detail="Could not find a usable table of contents or headings in the uploaded materials",
                ) from exc

        modules = outline.get("modules")
        if not isinstance(modules, list) or not modules:
            raise HTTPException(
                status_code=502,
                detail="Could not create a curriculum outline from the uploaded materials",
            )
        modules = self._enrich_module_descriptions_from_source(
            modules=modules,
            full_text=full_text,
        )

        curriculum_title = clean_vietnamese_text(
            str(outline.get("title") or f"Curriculum for {project.name}")
        ).strip() or f"Curriculum for {project.name}"
        curriculum_overview = clean_vietnamese_text(
            str(outline.get("overview") or "")
        ).strip()

        curriculum = Curriculums(
            project_id=project_id,
            title=curriculum_title,
            overview=curriculum_overview or None,
            generated_by=generated_by,
            total_module=len(modules),
            ready_module=0,
        )
        session.add(curriculum)
        session.commit()
        session.refresh(curriculum)

        created_modules = self._create_pending_modules(
            session=session,
            curriculum=curriculum,
            modules=modules,
            preview_count=preview_count,
        )

        preview_modules = self._ensure_preview_modules_ready(
            session=session,
            curriculum=curriculum,
            modules=created_modules,
            project_id=project_id,
            preview_count=preview_count,
        )

        all_modules = self._get_curriculum_modules(
            session=session,
            curriculum_id=curriculum.id,
        )
        self._sync_curriculum_progress(
            session=session,
            curriculum=curriculum,
            modules=all_modules,
        )
        question_meta = self._ensure_question_set_for_modules(
            session=session,
            project_id=project_id,
            curriculum=curriculum,
            modules=all_modules,
        )
        session.refresh(curriculum)
        return {
            "message": "Curriculum created with preview lessons",
            "curriculum_id": str(curriculum.id),
            "total_module": curriculum.total_module,
            "ready_module": curriculum.ready_module,
            **question_meta,
            "modules": preview_modules,
        }

    def ensure_module_ready(
        self,
        *,
        session: Session,
        module_id: uuid.UUID,
    ) -> CurriculumModules:
        curriculum, module = self._get_module_context_or_404(
            session=session,
            module_id=module_id,
        )

        if module.generate_status == "ready" and module.content:
            return module

        if module.generate_status == "generating":
            return module

        full_text = self._collect_project_material_text(
            session=session,
            project_id=curriculum.project_id,
        )

        try:
            return self._generate_module_content(
                session=session,
                curriculum=curriculum,
                module=module,
                full_text=full_text,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail=f"AI service failed to generate module content: {exc}",
            ) from exc

    def prefetch_next_modules(
        self,
        *,
        session: Session,
        module_id: uuid.UUID,
        limit: int = 2,
    ) -> list[CurriculumModules]:
        curriculum, current_module = self._get_module_context_or_404(
            session=session,
            module_id=module_id,
        )

        next_modules = session.exec(
            select(CurriculumModules)
            .where(
                CurriculumModules.curriculum_id == curriculum.id,
                CurriculumModules.order_index > (current_module.order_index or 0),
                CurriculumModules.generate_status.in_(("pending", "failed")),
            )
            .order_by(CurriculumModules.order_index)
            .limit(limit)
        ).all()

        if not next_modules:
            return []

        full_text = self._collect_project_material_text(
            session=session,
            project_id=curriculum.project_id,
        )

        generated_modules: list[CurriculumModules] = []
        for module in next_modules:
            try:
                generated_modules.append(
                    self._generate_module_content(
                        session=session,
                        curriculum=curriculum,
                        module=module,
                        full_text=full_text,
                    )
                )
            except Exception as exc:
                logger.warning(
                    "Prefetch lesson generation failed. curriculum_id=%s module_id=%s error_type=%s error=%s",
                    curriculum.id,
                    module.id,
                    type(exc).__name__,
                    exc,
                )

        self._sync_curriculum_progress(
            session=session,
            curriculum=curriculum,
            modules=self._get_curriculum_modules(
                session=session,
                curriculum_id=curriculum.id,
            ),
        )
        return generated_modules

    def prefetch_next_modules_background(
        self,
        *,
        module_id: uuid.UUID,
        limit: int = 2,
    ) -> None:
        with Session(engine) as session:
            self.prefetch_next_modules(
                session=session,
                module_id=module_id,
                limit=limit,
            )
