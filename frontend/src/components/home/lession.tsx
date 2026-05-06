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

const statusLabels: Record<string, string> = {
  pending: "Cho tao",
  generating: "Dang tao",
  ready: "San sang",
  failed: "Loi",
};

export default function Lession() {
  const { moduleId } = useParams();
  const navigate = useNavigate();

  const [lesson, setLesson] = useState<LessonDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    const loadLesson = async () => {
      if (!moduleId) {
        setLesson(null);
        setError("Khong tim thay bai hoc.");
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
      } catch {
        if (!isMounted) {
          return;
        }
        setLesson(null);
        setError("Khong the tai bai hoc nay.");
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

    const confirmed = window.confirm("Ban co chac chan muon xoa bai hoc nay?");
    if (!confirmed) {
      return;
    }

    try {
      setDeleting(true);
      setError(null);
      await api.delete(`/curriculum-modules/module/${moduleId}`);
      navigate("/projects");
    } catch {
      setError("Khong the xoa bai hoc nay.");
    } finally {
      setDeleting(false);
    }
  };

  const statusLabel = statusLabels[lesson?.generate_status ?? "pending"] ?? "Cho tao";
  const headingTitle = lesson?.title ?? "Bai hoc AI";

  return (
    <main className="lession">
      <div className="lession-banner lession-banner--a" />
      <div className="lession-banner lession-banner--b" />
      <div className="lession-banner lession-banner--c" />

      <section className="lession-header">
        <header className="lession-header__title">
          <div className="lession-header__head">
            <div className="lession-header__copy">
              <p className="lession-detail__eyebrow">Lesson Detail</p>
              <h2 className="lession-header__heading">{headingTitle}</h2>
              <p className="lession-header__description">
                Trang nay hien thi noi dung chi tiet cua mot bai hoc trong project.
              </p>
            </div>
          </div>

          <div className="lession-header__button">
            <Link to="/projects" className="lession-header__button--add">
              <ArrowLeft size={16} />
              Projects
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
                <span>Dang tai bai hoc va hoan thien noi dung...</span>
              </div>
            ) : lesson?.generate_status !== "ready" ? (
              <div className="lession-detail__empty">
                <Clock3 size={18} />
                <span>AI dang chuan bi bai hoc nay. Thu tai lai sau.</span>
              </div>
            ) : (
              <article className="lession-detail__article">
                {lesson.description ? (
                  <p className="lession-detail__summary">{lesson.description}</p>
                ) : null}
                <div className="lession-detail__content">
                  {lesson.content ?? "Chua co noi dung bai hoc."}
                </div>
              </article>
            )}
          </section>

          <aside className="lession-section">
            <div className="lession-section__head">
              <h3>Thong tin bai hoc</h3>
            </div>

            <div className="lession-detail__meta">
              <div className="lession-detail__meta-item">
                <span>Trang thai</span>
                <strong>{statusLabel}</strong>
              </div>
              <div className="lession-detail__meta-item">
                <span>Preview</span>
                <strong>{lesson?.is_preview ? "Co" : "Khong"}</strong>
              </div>
              <div className="lession-detail__meta-item">
                <span>Thu tu</span>
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
                  Lam bai trac nghiem
                </Link>
              ) : null}
              <button
                type="button"
                className="lession-detail__delete"
                onClick={() => void handleDelete()}
                disabled={loading || deleting}
              >
                <Trash2 size={16} />
                {deleting ? "Dang xoa..." : "Xoa bai hoc"}
              </button>
            </div>
          </aside>
        </section>
      </section>
    </main>
  );
}
