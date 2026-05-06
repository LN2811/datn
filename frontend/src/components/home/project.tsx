import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ArrowRight,
  CircleAlert,
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
        setError("Khong the tai du lieu du an.");
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

  const handleGenerateLessons = async () => {
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
        `Da tao bai hoc tu tai lieu va ${generationResponse.data.questions_count ?? 0} cau hoi.`,
      );
    } catch {
      setError("Khong the tao bai hoc tu tai lieu.");
    } finally {
      setGeneratingLessons(false);
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
      setError("Failed to delete material.");
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

  const title = project?.name ?? "Du an";
  const description = loading
    ? "Dang tai du an..."
    : error ?? project?.description ?? "";

  const getLessonStatusLabel = (status?: string | null) => {
    switch (status) {
      case "ready":
        return "San sang";
      case "generating":
        return "Dang tao";
      case "failed":
        return "Loi";
      default:
        return "Cho tao";
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
              <button
                className="study-dashboard__ghost-link"
                type="button"
                onClick={handleGenerateLessons}
                disabled={loading || generatingLessons}
              >
                <LayoutDashboard size={18} />
                {generatingLessons ? "Dang tao..." : "Tao bai hoc tu tai lieu"}
              </button>

              <button
                className="study-dashboard__ghost-link"
                type="button"
                aria-label="Upload project"
                onClick={() => setOpen(true)}
              >
                <Upload size={18} />
              </button>

              <Link className="study-dashboard__ghost-link" to="/">
                <ArrowRight size={18} />
                Trang Home
              </Link>
            </div>
          </header>

          <section className="project-session">
            <div>
              <section className="project-section">
                <div className="header-section">
                  <h2>Thong tin cac bai hoc</h2>
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
                    <span>Khong co bai hoc nao trong du an.</span>
                  </div>
                ) : (
                  <div className="project-section__list">
                    {lessons.map((lesson) => (
                      <Link
                        key={lesson.id}
                        to={`/lession/${lesson.id}`}
                        className="project-section__item"
                      >
                        <div className="project-section__item-header">
                          <div className="project-lesson__header">
                            <div>
                              <h3 style={{marginBlockStart: "0px"}}>{lesson.title ?? lesson.name ?? "Lesson"}</h3>
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
                                    Preview
                                  </span>
                                ) : null}
                              </div>
                            </div>
                          </div>
                        </div>
                      </Link>
                    ))}
                  </div>
                )}
              </section>
            </div>

            <aside className="project-aside">
              <section className="project-section--aside">
                <div>
                  <h2>Thong tin tai lieu</h2>
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
                    <span>Khong co tai lieu nao trong du an.</span>
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
                              Xem tai lieu
                            </a>
                            <button type="button" title="Xoa tai lieu" className="delete-button" onClick={() => void handledeletedocument(document.id)}>
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
          if (!projectId) {
            return;
          }

          void fetchDocuments(projectId)
            .then((data) => setDocuments(data))
            .catch(() => setError("Failed to refresh documents."));

          void fetchLessons(projectId)
            .then((data) => setLessons(data))
            .catch(() => setError("Failed to refresh lessons."));
        }}
      />
    </>
  );
}
