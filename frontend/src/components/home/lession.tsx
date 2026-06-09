import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, CircleAlert, Clock3, ListChecks, Sparkles, Trash2 } from "lucide-react";

import { api } from "@/api/axios";

import "./lession.css";


type LessonDetail = {
  id: string;
  curriculum_id: string;
  title: string;
  description?: string | null;
  content?: string | null;
  generate_status?: string | null;
  is_preview?: boolean;
  order_index?: number | null;
};

type CurriculumDetail = {
  id: string;
  project_id: string;
};

const statusLabels: Record<string, string> = {
  pending: "Chờ tạo",
  generating: "Đang tạo",
  ready: "Sẵn sàng",
  failed: "Lỗi",
};

function Lession() {
  const { moduleId } = useParams();
  const navigate = useNavigate();

  const [lesson, setLesson] = useState<LessonDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [projectId, setProjectId] = useState<string | null>(null);
  useEffect(() => {
    let isMounted = true;

    const loadLesson = async () => {
      if (!moduleId) {
        setLesson(null);
        setError("Không tìm thấy bài học.");
        setLoading(false);
        return;
      }

      setLoading(true);
      setError(null);
      setNotice(null);

      try {
        const detailResponse = await api.get<LessonDetail>(
          `/curriculum-modules/module/${moduleId}`,
        );

        if (!isMounted) {
          return;
        }

        let lessonData = detailResponse.data;

        if (lessonData.generate_status === "ready") {
          setLesson(lessonData);
          void api.post(`/curriculum-modules/module/${moduleId}/prefetch-next`).catch(
            () => undefined,
          );
        } else {
          const readyResponse = await api.post<LessonDetail>(
            `/curriculum-modules/module/${moduleId}/ensure-ready`,
          );
          if (!isMounted) {
            return;
          }
          lessonData = readyResponse.data;
          setLesson(lessonData);
        }

        try {
          const curriculumResponse = await api.get<CurriculumDetail>(
            `/curriculums/${lessonData.curriculum_id}`,
          );
          if (isMounted) {
            setProjectId(curriculumResponse.data.project_id);
          }
        } catch {
          if (isMounted) {
            setProjectId(null);
          }
        }
      } catch {
        if (!isMounted) {
          return;
        }
        setLesson(null);
        setError("Không thể tải bài học này.");
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    void loadLesson();

    return () => {
      isMounted = false;
    };
  }, [moduleId]);

  const handleDelete = async () => {
    if (!moduleId || deleting) {
      return;
    }

    const confirmed = window.confirm("Bạn có chắc chắn muốn xóa bài học này?");
    if (!confirmed) {
      return;
    }

    try {
      setDeleting(true);
      setError(null);
      await api.delete(`/curriculum-modules/module/${moduleId}`);
      navigate(projectId ? `/projects/${projectId}` : "/projects");
    } catch {
      setError("Không thể xóa bài học.");
    } finally {
      setDeleting(false);
    }
  };

  const statusLabel = statusLabels[lesson?.generate_status ?? "pending"] ?? "Chờ tạo";
  const headingTitle = lesson?.title ?? "Bài học";

  const backToProjectLink = projectId ? `/projects/${projectId}` : "/projects";

  return (
    <main className="lession">
      <div className="lession-banner lession-banner--a" />
      <div className="lession-banner lession-banner--b" />
      <div className="lession-banner lession-banner--c" />

      <section className="lession-header">
        <header className="lession-header__title">
          <div className="lession-header__head">
            <div className="lession-header__copy">
              <p className="lession-detail__eyebrow">Chi tiết bài học</p>
              <h2 className="lession-header__heading">{headingTitle}</h2>
              <p className="lession-header__description">
                Trang này hiển thị chi tiết bài học trong dự án của bạn.
              </p>
            </div>
          </div>

          <div className="lession-header__button">
            <Link to={backToProjectLink} className="lession-header__button--add">
              <ArrowLeft size={16} />
              Dự án
            </Link>
          </div>
        </header>

        <section className="lession-content">
          <section className="lession-section">
            {error ? (
              <div className="lession-detail__banner lession-detail__banner--error">
                <CircleAlert size={18} />
                <span>{error}</span>
              </div>
            ) : null}

            {notice ? (
              <div className="lession-detail__banner lession-detail__banner--success">
                <Sparkles size={18} />
                <span>{notice}</span>
              </div>
            ) : null}

            {loading ? (
              <div className="lession-detail__empty">
                <Clock3 size={18} />
                <span>Đang tải bài học và hoàn thiện nội dung...</span>
              </div>
            ) : lesson?.generate_status !== "ready" ? (
              <div className="lession-detail__empty">
                <Clock3 size={18} />
                <span>Hệ thống đang chuẩn bị bài học.</span>
              </div>
            ) : (
              <article className="lession-detail__article">
                {lesson.description ? (
                  <p className="lession-detail__summary">{lesson.description}</p>
                ) : null}
                <div className="lession-detail__content">
                  {lesson.content ?? "Chưa có nội dung bài học."}
                </div>
              </article>
            )}
          </section>

          <aside className="lession-section">
            <div className="lession-section__head">
              <h3>Thông tin bài học</h3>
            </div>

            <div className="lession-detail__meta">
              <div className="lession-detail__meta-item">
                <span>Trạng thái</span>
                <strong>{statusLabel}</strong>
              </div>
              <div className="lession-detail__meta-item">
                <span>Bản xem trước</span>
                <strong>{lesson?.is_preview ? "Có" : "Không"}</strong>
              </div>
              <div className="lession-detail__meta-item">
                <span>Thứ tự</span>
                <strong>{lesson?.order_index ?? "-"}</strong>
              </div>
            </div>

            <div className="lession-detail__actions">
              {moduleId && lesson?.generate_status === "ready" ? (
                <Link
                  to={`/lession/${moduleId}/quiz`}
                  className="lession-detail__quiz"
                >
                  <ListChecks size={16} />
                  Làm bài trắc nghiệm
                </Link>
              ) : null}
              <button
                type="button"
                className="lession-detail__delete"
                onClick={() => void handleDelete()}
                disabled={loading || deleting}
              >
                <Trash2 size={16} />
                {deleting ? "Đang xóa..." : "Xóa bài học"}
              </button>
            </div>
          </aside>
        </section>
      </section>
    </main>
  );
}

export default Lession;
