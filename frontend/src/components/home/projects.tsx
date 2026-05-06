import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  CircleAlert,
  Clock3,
  FolderKanban,
  Sparkles,
  Target,
  Trash2,
  UserRound,
} from "lucide-react";

import { api } from "@/api/axios";

import "./lession.css";
import CreateProject from "../../modal/createrproject";

type AssessmentOverview = {
  total_score?: number | null;
  readiness_level?: string | null;
  created_at?: string | null;
};

type ProjectOverview = {
  id: string;
  name: string;
  description?: string | null;
  is_owner: boolean;
  assignments_total: number;
  assignments_completed: number;
  assignments_pending: number;
  progress_percentage: number;
  materials_count: number;
  submissions_total: number;
  last_activity_at?: string | null;
  next_action: string;
  latest_assessment?: AssessmentOverview | null;
};

type DashboardSummary = {
  total_projects: number;
  tracked_assignments: number;
  submitted_assignments: number;
  average_progress: number;
  assessments_completed: number;
  attention_needed: number;
  last_activity_at?: string | null;
};

type DashboardOverview = {
  summary: DashboardSummary;
  projects: ProjectOverview[];
};

type CreatedProject = {
  id: string;
  name: string;
  description?: string | null;
};

const formatDateTime = (value?: string | null) => {
  if (!value) {
    return "Chua cap nhat";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "Chua cap nhat";
  }

  return parsed.toLocaleString("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
};

const getReadinessMeta = (level?: string | null) => {
  switch (level) {
    case "high":
      return {
        label: "San sang cao",
        tone: "high",
      };
    case "medium":
      return {
        label: "San sang trung binh",
        tone: "medium",
      };
    case "low":
      return {
        label: "Can cuong co",
        tone: "low",
      };
    default:
      return {
        label: "Chua danh gia",
        tone: "neutral",
      };
  }
};

export default function ProjectsPage() {
  const navigate = useNavigate();

  const [projects, setProjects] = useState<ProjectOverview[]>([]);
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [deletingProjectId, setDeletingProjectId] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isCreateProjectOpen, setIsCreateProjectOpen] = useState(false);

  const loadProjects = async () => {
    const overviewResponse = await api.get<DashboardOverview>("/projects/overview");
    setProjects(overviewResponse.data.projects ?? []);
    setSummary(overviewResponse.data.summary ?? null);
  };

  useEffect(() => {
    let isMounted = true;

    const loadData = async () => {
      setLoading(true);
      setError(null);
      setNotice(null);

      try {
        const overviewResponse = await api.get<DashboardOverview>("/projects/overview");
        if (!isMounted) {
          return;
        }

        setProjects(overviewResponse.data.projects ?? []);
        setSummary(overviewResponse.data.summary ?? null);
      } catch {
        if (!isMounted) {
          return;
        }
        setProjects([]);
        setSummary(null);
        setError("Khong the tai danh sach project.");
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    void loadData();

    return () => {
      isMounted = false;
    };
  }, []);

  const handleDeleteProject = async (projectId: string) => {
    if (deletingProjectId) {
      return;
    }

    const targetProject = projects.find((project) => project.id === projectId);
    const confirmed = window.confirm(
      `Ban co chac chan muon xoa project "${targetProject?.name ?? "nay"}"?`,
    );
    if (!confirmed) {
      return;
    }

    try {
      setDeletingProjectId(projectId);
      setError(null);
      setNotice(null);

      await api.delete(`/projects/${projectId}`);
      await loadProjects();
      setNotice("Da xoa project.");
    } catch {
      setError("Khong the xoa project nay.");
    } finally {
      setDeletingProjectId(null);
    }
  };

  const handleCreateProjectSuccess = async (createdProject: CreatedProject) => {
    setNotice("Da tao project.");
    setError(null);

    if (createdProject.id) {
      navigate(`/projects/${createdProject.id}`);
      return;
    }

    try {
      setLoading(true);
      await loadProjects();
    } catch {
      setError("Da tao project, nhung khong the tai lai danh sach project.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <main className="lession">
        <div className="lession-banner lession-banner--a" />
        <div className="lession-banner lession-banner--b" />
        <div className="lession-banner lession-banner--c" />

        <section className="lession-header">
          <header className="lession-header__title">
            <div className="lession-header__head">
              <div className="lession-header__copy">
                <p className="lession-detail__eyebrow">Projects Workspace</p>
                <h2 className="lession-header__heading">Tat ca project cua ban</h2>
                <p className="lession-header__description">
                  Day la noi hien thi toan bo project ma ban dang so huu hoac tham gia.
                </p>
              </div>
            </div>

            <div className="lession-header__button">
              <Link to="/dashboard" className="lession-header__button--add">
                <ArrowLeft size={16} />
                Dashboard
              </Link>
              <button
                className="lession-header__button--add"
                type="button"
                onClick={() => setIsCreateProjectOpen(true)}
              >
                Tao Project
              </button>
            </div>
          </header>

          <section className="lession-content lession-content--projects">
            <section className="lession-section">
              <div className="lession-section__head">
                <div>
                  <h3>Danh sach project</h3>
                  <p className="lession-section__copy">
                    Mo tung project de xem bai hoc, tai lieu, va thao tac AI lien quan.
                  </p>
                </div>
                <FolderKanban size={20} />
              </div>

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
                  <span>Dang tai danh sach project cua ban...</span>
                </div>
              ) : projects.length === 0 ? (
                <div className="lession-detail__empty">
                  <Sparkles size={18} />
                  <span>Ban chua co project nao de hien thi.</span>
                </div>
              ) : (
                <div className="lession-project__list">
                  {projects.map((project) => {
                    const readinessMeta = getReadinessMeta(
                      project.latest_assessment?.readiness_level,
                    );

                    return (
                      <article key={project.id} className="lession-project__card">
                        <div className="lession-project__top">
                          <div className="lession-project__copy">
                            <div className="lession-project__meta">
                              <span className="lession-project__pill">
                                <FolderKanban size={14} />
                                Project
                              </span>
                              <span className="lession-project__pill">
                                <UserRound size={14} />
                                {project.is_owner ? "So huu" : "Dang tham gia"}
                              </span>
                              <span
                                className={`lession-project__pill lession-project__pill--${readinessMeta.tone}`}
                              >
                                {readinessMeta.label}
                              </span>
                            </div>

                            <h3>{project.name}</h3>
                            <p>
                              {project.description?.trim()
                                ? project.description
                                : "Project chua co mo ta. Ban van co the mo project de xem tai lieu va bai hoc."}
                            </p>
                          </div>

                          <div className="lession-project__actions">
                            <Link className="lession-project__link" to={`/projects/${project.id}`}>
                              Mo project
                            </Link>
                            <button
                              type="button"
                              className="lession-project__delete"
                              onClick={() => void handleDeleteProject(project.id)}
                              disabled={deletingProjectId !== null || !project.is_owner}
                              title={
                                project.is_owner
                                  ? "Xoa project"
                                  : "Chi chu so huu moi co the xoa project"
                              }
                            >
                              <Trash2 size={16} />
                              {deletingProjectId === project.id ? "Dang xoa..." : "Xoa project"}
                            </button>
                          </div>
                        </div>

                        <div className="lession-project__stats">
                          <div className="lession-project__stat">
                            <span>Bai tap</span>
                            <strong>{project.assignments_total}</strong>
                          </div>
                          <div className="lession-project__stat">
                            <span>Da nop</span>
                            <strong>{project.assignments_completed}</strong>
                          </div>
                          <div className="lession-project__stat">
                            <span>Con lai</span>
                            <strong>{project.assignments_pending}</strong>
                          </div>
                          <div className="lession-project__stat">
                            <span>Tai lieu</span>
                            <strong>{project.materials_count}</strong>
                          </div>
                        </div>

                        <div className="lession-project__progress">
                          <div className="lession-project__progress-head">
                            <span>Tien do hoan thanh</span>
                            <strong>{project.progress_percentage}%</strong>
                          </div>
                          <div className="lession-project__progress-track" aria-hidden="true">
                            <div
                              className="lession-project__progress-fill"
                              style={{ width: `${project.progress_percentage}%` }}
                            />
                          </div>
                        </div>

                        <div className="lession-project__next-step">
                          <Target size={16} />
                          <span>{project.next_action}</span>
                        </div>
                      </article>
                    );
                  })}
                </div>
              )}
            </section>

            <aside className="lession-section">
              <div className="lession-section__head">
                <div>
                  <h3>Tong quan nhanh</h3>
                  <p className="lession-section__copy">
                    Tom tat toan bo project cua ban tren cung mot trang.
                  </p>
                </div>
                <Sparkles size={20} />
              </div>

              <div className="lession-summary__grid">
                <div className="lession-detail__meta-item">
                  <span>Tong project</span>
                  <strong>{summary?.total_projects ?? 0}</strong>
                </div>
                <div className="lession-detail__meta-item">
                  <span>Tien do trung binh</span>
                  <strong>{summary?.average_progress ?? 0}%</strong>
                </div>
                <div className="lession-detail__meta-item">
                  <span>Bai tap da nop</span>
                  <strong>
                    {summary?.submitted_assignments ?? 0}/{summary?.tracked_assignments ?? 0}
                  </strong>
                </div>
                <div className="lession-detail__meta-item">
                  <span>Lan danh gia</span>
                  <strong>{summary?.assessments_completed ?? 0}</strong>
                </div>
                <div className="lession-detail__meta-item">
                  <span>Can chu y</span>
                  <strong>{summary?.attention_needed ?? 0} project</strong>
                </div>
                <div className="lession-detail__meta-item">
                  <span>Hoat dong gan nhat</span>
                  <strong>{formatDateTime(summary?.last_activity_at)}</strong>
                </div>
              </div>
            </aside>
          </section>
        </section>
      </main>

      <CreateProject
        open={isCreateProjectOpen}
        onClose={() => setIsCreateProjectOpen(false)}
        onSuccess={(createdProject) => void handleCreateProjectSuccess(createdProject)}
      />
    </>
  );
}
