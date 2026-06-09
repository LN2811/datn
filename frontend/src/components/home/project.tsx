import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ArrowRight,
  CircleAlert,
  Github,
  GraduationCap,
  LayoutDashboard,
  Upload,
  Trash
} from "lucide-react";

import { api } from "@/api/axios.ts";
import { getApiBaseUrl } from "@/api/baseUrl";
import UploadModal from "./Uploadmodal.tsx";

import "./project.css";

type ProjectDetail = {
  id: string;
  name: string;
  description?: string | null;
};

type ProjectLesson = {
  id: string;
  title?: string | null;
  name?: string | null;
  description?: string | null;
  content?: string | null;
  generate_status?: string | null;
  is_preview?: boolean;
  order_index?: number | null;
};

type ProjectDocument = {
  id: string;
  title: string;
  external_link?: string | null;
  file_path?: string | null;
};

type LessonGenerationResult = {
  question_assignment_id?: string | null;
  questions_count?: number | null;
};

export default function Project() {
  const { projectId } = useParams();

  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [lessons, setLessons] = useState<ProjectLesson[]>([]);
  const [documents, setDocuments] = useState<ProjectDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [generatingLessons, setGeneratingLessons] = useState(false);

  const uploadsBaseUrl = getApiBaseUrl();

  const fetchLessons = async (currentProjectId: string) => {
    const response = await api.get<ProjectLesson[]>(
      `/curriculums/projects/${currentProjectId}/lessons`,
    );
    return response.data;
  };

  const fetchDocuments = async (currentProjectId: string) => {
    const response = await api.get<ProjectDocument[]>(
      `/learning-materials/project/${currentProjectId}`,
    );
    return response.data;
  };

  useEffect(() => {
    let isMounted = true;

    const fetchData = async () => {
      if (!projectId) {
        setLoading(false);
        return;
      }

      setLoading(true);
      setError(null);
      setNotice(null);

      try {
        const [projectResponse, lessonsData, documentsData] = await Promise.all([
          api.get<ProjectDetail>(`/projects/${projectId}`),
          fetchLessons(projectId),
          fetchDocuments(projectId),
        ]);

        if (!isMounted) {
          return;
        }

        setProject(projectResponse.data);
        setLessons(lessonsData);
        setDocuments(documentsData);
      } catch {
        if (!isMounted) {
          return;
        }

        setProject(null);
        setLessons([]);
        setDocuments([]);
        setError("Không thể tải dữ liệu dự án.");
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    void fetchData();

    return () => {
      isMounted = false;
    };
  }, [projectId]);

  const generateLessonsFromMaterials = async (successMessage?: string) => {
    if (!projectId || generatingLessons) {
      return;
    }

    try {
      setGeneratingLessons(true);
      setError(null);
      setNotice(null);

      const generationResponse = await api.post<LessonGenerationResult>(
        `/curriculums/projects/${projectId}/generate-lessons?force_regenerate=true`,
      );
      const refreshedLessons = await fetchLessons(projectId);
      setLessons(refreshedLessons);
      setNotice(
        successMessage ??
          `Đã tạo bài học từ tài liệu và ${generationResponse.data.questions_count ?? 0} câu hỏi.`,
      );
    } catch {
      setError("Không thể tạo bài học từ tài liệu.");
    } finally {
      setGeneratingLessons(false);
    }
  };

  const handleGenerateLessons = async () => {
    await generateLessonsFromMaterials();
  };

  const handleUploadMaterialSuccess = async () => {
    if (!projectId) {
      return;
    }

    setOpen(false);
    setError(null);
    setNotice("Đã tải tài liệu lên. Đang cập nhật bài học...");

    try {
      const refreshedDocuments = await fetchDocuments(projectId);
      setDocuments(refreshedDocuments);
      await generateLessonsFromMaterials("Đã tải tài liệu lên và cập nhật bài học từ tài liệu mới.");
    } catch {
      setError("Không thể tải lại danh sách tài liệu.");
    }
  };
  const handledeletedocument = async (documentId: string) => {
    if (!projectId) {
      return;
    }

    try {
      await api.delete(`/learning-materials/${documentId}`);
      setDocuments((prev) =>
        prev.filter((document) => document.id !== documentId),
      );
    } catch {
      setError("Không thể xóa tài liệu.");
    }
  };

  const getDocumentHref = (document: ProjectDocument) => {
    if (document.external_link) {
      return document.external_link;
    }

    if (!document.file_path) {
      return null;
    }

    const fileName = document.file_path.split(/[/\\]/).pop();
    if (!fileName) {
      return null;
    }

    return `${uploadsBaseUrl}/uploads/${fileName}`;
  };

  const title = project?.name ?? "Dự án";
  const description = loading
    ? "Đang tải dự án..."
    : error ?? project?.description ?? "";
  const firstLesson = lessons[0] ?? null;

  const getLessonStatusLabel = (status?: string | null) => {
    switch (status) {
      case "ready":
        return "Sẵn sàng";
      case "generating":
        return "Đang tạo";
      case "failed":
        return "Lỗi";
      default:
        return "Chờ tạo";
    }
  };

  const getLessonStatusClass = (status?: string | null) => {
    switch (status) {
      case "ready":
        return "project-lesson__badge--ready";
      case "generating":
        return "project-lesson__badge--generating";
      case "failed":
        return "project-lesson__badge--failed";
      default:
        return "project-lesson__badge--pending";
    }
  };

  return (
    <>
      <main className="main-project">
        <div className="project-banner project-banner--a" />
        <div className="project-banner project-banner--b" />
        <div className="project-banner project-banner--c" />

        <section className="project-header">
          <header className="project-header__content">
            <div className="project-header__intro">
              <h1>{title}</h1>
              {description ? (
                <p className="project-header__description">{description}</p>
              ) : null}
            </div>

            <div className="project-header__actions">
              {firstLesson ? (
                <Link
                  to={`/lession/${firstLesson.id}/code_review`}
                  className="project-lesson__link project-lesson__link--github"
                >
                  <Github size={16} />
                  Nộp GitHub
                </Link>
              ) : (
                <button
                  className="project-lesson__link project-lesson__link--github"
                  type="button"
                  disabled
                >
                  <Github size={16} />
                  Nộp GitHub
                </button>
              )}
              <button
                className="study-dashboard__ghost-link"
                type="button"
                onClick={handleGenerateLessons}
                disabled={loading || generatingLessons}
              >
                <LayoutDashboard size={18} />
                {generatingLessons ? "Đang tạo..." : "Tạo bài học từ tài liệu"}
              </button>

              <button
                className="study-dashboard__ghost-link project-header__upload-button"
                type="button"
                aria-label="Tải tài liệu lên"
                onClick={() => setOpen(true)}
                disabled={loading || !projectId}
              >
                <Upload size={18} />
                Tải tài liệu
              </button>

              <Link className="study-dashboard__ghost-link" to="/">
                <ArrowRight size={18} />
                Trang chủ
              </Link>
            </div>
          </header>

          <section className="project-session">
            <div>
              <section className="project-section">
                <div className="header-section">
                  <h2>Thông tin các bài học</h2>
                  <LayoutDashboard size={18} />
                </div>

                {error ? (
                  <div className="project-error">
                    <CircleAlert size={18} />
                    <span>{error}</span>
                  </div>
                ) : null}
                {notice ? (
                  <div className="project-notice">
                    <GraduationCap size={18} />
                    <span>{notice}</span>
                  </div>
                ) : null}
                {loading ? (
                  <div>
                    {Array.from({ length: 3 }).map((_, index) => (
                      <article
                        key={index}
                        className="project-section__item project-section__item--loading"
                      >
                        <div className="project-section__item-header" />
                        <div className="project-section__item-content" />
                      </article>
                    ))}
                  </div>
                ) : lessons.length === 0 ? (
                  <div className="project-empty">
                    <GraduationCap size={18} />
                    <span>Không có bài học nào trong dự án.</span>
                  </div>
                ) : (
                  <div className="project-section__list">
                    {lessons.map((lesson) => (
                      <article key={lesson.id} className="project-section__item">
                        <div className="project-section__item-header">
                          <div className="project-lesson__header">
                            <div>
                              <h3 style={{marginBlockStart: "0px"}}>{lesson.title ?? lesson.name ?? "Bài học"}</h3>
                              <div className="project-lesson__badges">
                                <span
                                  className={`project-lesson__badge ${getLessonStatusClass(
                                    lesson.generate_status,
                                  )}`}
                                >
                                  {getLessonStatusLabel(lesson.generate_status)}
                                </span>

                                {lesson.is_preview ? (
                                  <span className="project-lesson__badge project-lesson__badge--preview">
                                    Bản xem trước
                                  </span>
                                ) : null}
                              </div>
                            </div>
                            <div className="project-lesson__actions">
                              <Link
                                to={`/lession/${lesson.id}`}
                                className="project-lesson__link"
                              >
                                <ArrowRight size={16} />
                                Bài học
                              </Link>
                            </div>
                          </div>
                        </div>
                      </article>
                    ))}
                  </div>
                )}
              </section>
            </div>

            <aside className="project-aside">
              <section className="project-section--aside">
                <div>
                  <h2>Thông tin tài liệu</h2>
                </div>

                {loading ? (
                  <div>
                    {Array.from({ length: 3 }).map((_, index) => (
                      <article
                        key={index}
                        className="project-section__item project-section__item--loading"
                      >
                        <div className="project-section__item-header" />
                        <div className="project-section__item-content" />
                      </article>
                    ))}
                  </div>
                ) : documents.length === 0 ? (
                  <div className="project-empty">
                    <GraduationCap size={18} />
                    <span>Không có tài liệu nào trong dự án.</span>
                  </div>
                ) : (
                  <div className="project-section__list">
                    {documents.map((document) => (
                      <article key={document.id} className="project-section__item">
                       <div className="document-item">
                          <div className="project-section__item-header">
                            <h3>{document.title}</h3>
                          </div>

                          <div className="project-section__item-content">
                            <a
                              href={getDocumentHref(document) ?? undefined}
                              target="_blank"
                              rel="noopener noreferrer"
                            >
                              Xem tài liệu
                            </a>
                            <button type="button" title="Xóa tài liệu" className="delete-button" onClick={() => void handledeletedocument(document.id)}>
                              <Trash size={16} />
                            </button>
                          </div>
                       </div>
                      </article>
                    ))}
                  </div>
                )}
              </section>
            </aside>
          </section>
        </section>
      </main>

      <UploadModal
        open={open}
        onClose={() => setOpen(false)}
        projectId={projectId ?? ""}
        onUploadSuccess={() => {
          void handleUploadMaterialSuccess();
        }}
      />
    </>
  );
}
