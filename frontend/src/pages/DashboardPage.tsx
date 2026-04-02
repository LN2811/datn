import { useEffect, useState } from 'react';
import {
  ArrowRight,
  BookOpen,
  Brain,
  Briefcase,
  CheckCircle2,
  CircleAlert,
  Clock3,
  FileText,
  FolderKanban,
  GraduationCap,
  LayoutDashboard,
  LogOut,
  Plus,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Target,
  TrendingUp,
  UserRound,
  type LucideIcon,
} from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';

import { useAuth } from '../auth/AuthContext.tsx';
import { api } from '../api/axios.ts';

import './DashboardPage.css';

type AssignmentOverview = {
  id: string;
  title: string;
  description?: string | null;
  created_at?: string | null;
  submission_count: number;
  is_submitted: boolean;
  last_submitted_at?: string | null;
  best_score?: number | null;
};

type AssessmentOverview = {
  result_id: string;
  total_score?: number | null;
  readiness_level?: string | null;
  created_at?: string | null;
  analysis_text?: string | null;
  strengths?: string | null;
  weaknesses?: string | null;
  recommendations?: string | null;
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
  recent_assignments: AssignmentOverview[];
};

type DashboardOverview = {
  summary: {
    total_projects: number;
    tracked_assignments: number;
    submitted_assignments: number;
    average_progress: number;
    assessments_completed: number;
    attention_needed: number;
    last_activity_at?: string | null;
  };
  projects: ProjectOverview[];
};

type SummaryCard = {
  label: string;
  value: string;
  detail: string;
  icon: LucideIcon;
  tone: 'blue' | 'teal' | 'amber' | 'ink';
};

type CreateProjectPayload = {
  name: string;
  description: string;
};

const getDisplayName = (email?: string | null) => {
  if (!email) {
    return 'ban';
  }

  const localPart = email.split('@')[0] ?? email;
  const normalized = localPart.replace(/[._-]+/g, ' ').trim();

  if (!normalized) {
    return email;
  }

  return normalized
    .split(/\s+/)
    .map((chunk) => chunk.charAt(0).toUpperCase() + chunk.slice(1))
    .join(' ');
};

const formatDateTime = (value?: string | null) => {
  if (!value) {
    return 'Chua co du lieu';
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return 'Chua co du lieu';
  }

  return parsed.toLocaleString('vi-VN', {
    hour: '2-digit',
    minute: '2-digit',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  });
};

const formatShortDate = (value?: string | null) => {
  if (!value) {
    return 'Chua cap nhat';
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return 'Chua cap nhat';
  }

  return parsed.toLocaleDateString('vi-VN', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  });
};

const getReadinessMeta = (level?: string | null) => {
  switch (level) {
    case 'high':
      return {
        label: 'San sang cao',
        tone: 'high' as const,
        description: 'Nen tang tot, co the tiep tuc cac dau viec chinh.',
      };
    case 'medium':
      return {
        label: 'San sang trung binh',
        tone: 'medium' as const,
        description: 'Dang co nen tang, nhung can giam cac diem yeu hien tai.',
      };
    case 'low':
      return {
        label: 'Can cuong co',
        tone: 'low' as const,
        description: 'Nen uu tien kien thuc nen va lap lai nhip hoc on dinh.',
      };
    default:
      return {
        label: 'Chua danh gia',
        tone: 'empty' as const,
        description: 'Ban chua co ket qua tu danh gia cho project nay.',
      };
  }
};

const getAssignmentState = (assignment: AssignmentOverview) =>
  assignment.is_submitted
    ? {
        label: 'Da nop',
        tone: 'done' as const,
      }
    : {
        label: 'Chua nop',
        tone: 'pending' as const,
      };

const getPriorityRank = (project: ProjectOverview) => {
  const readinessLevel = project.latest_assessment?.readiness_level;
  if (!project.latest_assessment) {
    return 0;
  }
  if (readinessLevel === 'low') {
    return 1;
  }
  if (project.assignments_pending > 0) {
    return 2;
  }
  return 3;
};

const getErrorMessage = (error: unknown) => {
  if (
    typeof error === 'object' &&
    error !== null &&
    'response' in error &&
    typeof (error as { response?: unknown }).response === 'object' &&
    (error as { response?: { data?: { detail?: unknown } } }).response?.data?.detail
  ) {
    const detail = (error as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
    if (typeof detail === 'string') {
      return detail;
    }
  }

  if (error instanceof Error && error.message) {
    return error.message;
  }

  return 'Khong tai duoc dashboard. Vui long thu lai.';
};

const getCreateProjectErrorMessage = (error: unknown) => {
  if (
    typeof error === 'object' &&
    error !== null &&
    'response' in error &&
    typeof (error as { response?: unknown }).response === 'object' &&
    (error as { response?: { data?: { detail?: unknown } } }).response?.data?.detail
  ) {
    const detail = (error as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
    if (typeof detail === 'string') {
      return detail;
    }
  }

  if (error instanceof Error && error.message) {
    return error.message;
  }

  return 'Khong tao duoc project. Vui long thu lai.';
};

const validateProjectInput = (payload: CreateProjectPayload) => {
  if (!payload.name.trim()) {
    return 'Vui long nhap ten project.';
  }

  if (payload.name.trim().length < 3) {
    return 'Ten project can it nhat 3 ky tu.';
  }

  return null;
};

const loadDashboardOverview = async () => {
  const response = await api.get<DashboardOverview>('/projects/overview');
  return response.data;
};

export function DashboardPage() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [error, setError] = useState('');
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isCreatingProject, setIsCreatingProject] = useState(false);
  const [createProjectError, setCreateProjectError] = useState('');
  const [createProjectStatus, setCreateProjectStatus] = useState('');
  const [projectName, setProjectName] = useState('');
  const [projectDescription, setProjectDescription] = useState('');

  useEffect(() => {
    let isMounted = true;

    const loadOverview = async () => {
      try {
        const response = await loadDashboardOverview();
        if (!isMounted) {
          return;
        }
        setOverview(response);
        setError('');
      } catch (loadError) {
        if (!isMounted) {
          return;
        }
        setError(getErrorMessage(loadError));
      } finally {
        if (isMounted) {
          setIsLoading(false);
          setIsRefreshing(false);
        }
      }
    };

    void loadOverview();

    return () => {
      isMounted = false;
    };
  }, []);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    setError('');

    try {
      const response = await loadDashboardOverview();
      setOverview(response);
    } catch (loadError) {
      setError(getErrorMessage(loadError));
    } finally {
      setIsRefreshing(false);
    }
  };

  const resetCreateProjectForm = () => {
    setProjectName('');
    setProjectDescription('');
    setCreateProjectError('');
  };

  const handleCreateProject = async () => {
    const payload = {
      name: projectName.trim(),
      description: projectDescription.trim(),
    };
    const validationError = validateProjectInput(payload);
    if (validationError) {
      setCreateProjectError(validationError);
      return;
    }

    setIsCreatingProject(true);
    setCreateProjectError('');
    setCreateProjectStatus('');

    try {
      await api.post('/projects', payload);
      const response = await loadDashboardOverview();
      setOverview(response);
      setCreateProjectStatus('Da tao project moi thanh cong.');
      resetCreateProjectForm();
      setIsCreateOpen(false);
      setError('');
    } catch (createError) {
      setCreateProjectError(getCreateProjectErrorMessage(createError));
    } finally {
      setIsCreatingProject(false);
    }
  };

  const handleLogout = async () => {
    setIsLoggingOut(true);
    try {
      await logout();
      navigate('/login', { replace: true });
    } finally {
      setIsLoggingOut(false);
    }
  };

  const displayName = getDisplayName(user?.email);
  const projects = overview?.projects ?? [];
  const summary = overview?.summary;
  const topPriorities = [...projects]
    .sort((left, right) => getPriorityRank(left) - getPriorityRank(right))
    .slice(0, 3);

  const summaryCards: SummaryCard[] = [
    {
      label: 'Project dang theo hoc',
      value: String(summary?.total_projects ?? 0),
      detail: 'Tong so project ban dang co lien quan trong he thong.',
      icon: FolderKanban,
      tone: 'blue',
    },
    {
      label: 'Tien do trung binh',
      value: `${summary?.average_progress ?? 0}%`,
      detail: 'Ty le bai tap da nop tren tong bai tap duoc theo doi.',
      icon: TrendingUp,
      tone: 'teal',
    },
    {
      label: 'Bai tap da nop',
      value: `${summary?.submitted_assignments ?? 0}/${summary?.tracked_assignments ?? 0}`,
      detail: 'Muc do hoan thanh bai tap tren tat ca project cua ban.',
      icon: CheckCircle2,
      tone: 'amber',
    },
    {
      label: 'Lan tu danh gia',
      value: String(summary?.assessments_completed ?? 0),
      detail: 'So project da co ket qua danh gia muc do san sang hoc tap.',
      icon: Brain,
      tone: 'ink',
    },
  ];

  return (
    <main className="study-dashboard">
      <div className="study-dashboard__glow study-dashboard__glow--a" aria-hidden="true" />
      <div className="study-dashboard__glow study-dashboard__glow--b" aria-hidden="true" />
      <div className="study-dashboard__glow study-dashboard__glow--c" aria-hidden="true" />

      <div className="study-dashboard__shell">
        <header className="study-dashboard__bar">
          <div className="study-dashboard__bar-copy">
            <span className="study-dashboard__kicker">Signed-in learning dashboard</span>
            <h1>Chao mung tro lai, {displayName}.</h1>
            <p>
              Sau khi dang nhap, day la noi ban theo doi project dang hoc, tien do bai tap,
              ket qua tu danh gia, va cac goi y AI de quyet dinh buoc tiep theo.
            </p>
          </div>

          <div className="study-dashboard__bar-actions">
            <button
              className="study-dashboard__primary-link study-dashboard__primary-link--create"
              type="button"
              onClick={() => {
                setIsCreateOpen((current) => !current);
                setCreateProjectStatus('');
                setCreateProjectError('');
              }}
            >
              <Plus size={18} />
              {isCreateOpen ? 'Dong form tao project' : 'Tao project'}
            </button>
            <Link className="study-dashboard__ghost-link" to="/">
              <ArrowRight size={18} />
              Trang public
            </Link>
            {user?.is_superuser ? (
              <Link className="study-dashboard__ghost-link" to="/admin">
                <ShieldCheck size={18} />
                Admin
              </Link>
            ) : null}
            <button
              className="study-dashboard__ghost-link study-dashboard__ghost-link--button"
              type="button"
              onClick={handleRefresh}
              disabled={isRefreshing}
            >
              <RefreshCw size={18} className={isRefreshing ? 'study-dashboard__spin' : ''} />
              {isRefreshing ? 'Dang tai...' : 'Lam moi'}
            </button>
            <button
              className="study-dashboard__primary-link"
              type="button"
              onClick={handleLogout}
              disabled={isLoggingOut}
            >
              <LogOut size={18} />
              {isLoggingOut ? 'Dang xu ly...' : 'Dang xuat'}
            </button>
          </div>
        </header>

        <section className="study-dashboard__hero">
          <div className="study-dashboard__hero-main">
            <div className="study-dashboard__hero-head">
              <span className="study-dashboard__eyebrow">Overview</span>
              <h2>Bang tong hop qua trinh hoc va muc do san sang</h2>
              <p>
                Phan nay uu tien nhung gi can xem ngay: tong quan tien do, bai tap da nop,
                ket qua tu danh gia theo tung project, va muc nao dang can chu y hon.
              </p>
            </div>

            <div className="study-dashboard__summary-grid">
              {summaryCards.map((card) => (
                <article
                  key={card.label}
                  className={`study-dashboard__summary-card study-dashboard__summary-card--${card.tone}`}
                >
                  <div className="study-dashboard__summary-icon">
                    <card.icon size={20} />
                  </div>
                  <span>{card.label}</span>
                  <strong>{card.value}</strong>
                  <p>{card.detail}</p>
                </article>
              ))}
            </div>
          </div>

          <aside className="study-dashboard__hero-side">
            <div className="study-dashboard__panel">
              <div className="study-dashboard__panel-head">
                <div className="study-dashboard__avatar">
                  {displayName
                    .split(/\s+/)
                    .filter(Boolean)
                    .slice(0, 2)
                    .map((chunk) => chunk.charAt(0).toUpperCase())
                    .join('') || 'U'}
                </div>
                <div>
                  <span className="study-dashboard__panel-kicker">Tai khoan hien tai</span>
                  <h3>{user?.is_superuser ? 'Administrator' : 'Learner workspace'}</h3>
                </div>
              </div>

              <div className="study-dashboard__signal-list">
                <div className="study-dashboard__signal">
                  <span>
                    <Briefcase size={16} />
                    Email
                  </span>
                  <strong>{user?.email ?? 'Khong co du lieu'}</strong>
                </div>
                <div className="study-dashboard__signal">
                  <span>
                    <ShieldCheck size={16} />
                    Session
                  </span>
                  <strong>{user?.is_active ? 'Dang hoat dong' : 'Bi gioi han'}</strong>
                </div>
                <div className="study-dashboard__signal">
                  <span>
                    <CircleAlert size={16} />
                    Muc can chu y
                  </span>
                  <strong>{summary?.attention_needed ?? 0} project</strong>
                </div>
                <div className="study-dashboard__signal">
                  <span>
                    <Clock3 size={16} />
                    Hoat dong gan nhat
                  </span>
                  <strong>{formatDateTime(summary?.last_activity_at)}</strong>
                </div>
              </div>
            </div>
          </aside>
        </section>

        <section className="study-dashboard__content">
          <div className="study-dashboard__main">
            <section className="study-dashboard__section-card">
              <div className="study-dashboard__section-head">
                <div>
                  <span className="study-dashboard__section-kicker">Projects</span>
                  <h2>Cac project dang theo hoc</h2>
                </div>
                <LayoutDashboard size={20} />
              </div>

              {error ? (
                <div className="study-dashboard__banner study-dashboard__banner--error">
                  <CircleAlert size={18} />
                  <span>{error}</span>
                </div>
              ) : null}

              {isLoading ? (
                <div className="study-dashboard__project-list">
                  {Array.from({ length: 2 }).map((_, index) => (
                    <article key={index} className="study-dashboard__project-card study-dashboard__project-card--skeleton">
                      <div className="study-dashboard__skeleton study-dashboard__skeleton--title" />
                      <div className="study-dashboard__skeleton study-dashboard__skeleton--line" />
                      <div className="study-dashboard__skeleton study-dashboard__skeleton--line" />
                      <div className="study-dashboard__skeleton study-dashboard__skeleton--block" />
                    </article>
                  ))}
                </div>
              ) : projects.length === 0 ? (
                <div className="study-dashboard__empty">
                  <GraduationCap size={28} />
                  <div>
                    <h3>Chua co project nao de theo doi</h3>
                    <p>
                      Khi ban co project, bai tap, submission hoac ket qua tu danh gia, dashboard
                      nay se tu dong tong hop de hien thi tien do hoc tap.
                    </p>
                  </div>
                </div>
              ) : (
                <div className="study-dashboard__project-list">
                  {projects.map((project) => {
                    const readinessMeta = getReadinessMeta(project.latest_assessment?.readiness_level);

                    return (
                      <article key={project.id} className="study-dashboard__project-card">
                        <div className="study-dashboard__project-head">
                          <div>
                            <div className="study-dashboard__project-meta">
                              <span className="study-dashboard__pill study-dashboard__pill--neutral">
                                <FolderKanban size={14} />
                                Project
                              </span>
                              <span className="study-dashboard__pill study-dashboard__pill--neutral">
                                <UserRound size={14} />
                                {project.is_owner ? 'So huu' : 'Dang tham gia'}
                              </span>
                            </div>
                            <Link to={`/projects/${project.id}`} className="study-dashboard__project-link">
                              <h3>{project.name}</h3>
                              <p>
                                {project.description?.trim()
                                  ? project.description
                                  : 'Project chua co mo ta. Dashboard van theo doi assignment, submission va ket qua tu danh gia cua ban.'}
                              </p>
                            </Link>
                          </div>

                          <div className={`study-dashboard__readiness study-dashboard__readiness--${readinessMeta.tone}`}>
                            <span>{readinessMeta.label}</span>
                            <strong>
                              {project.latest_assessment?.total_score != null
                                ? `${Math.round(project.latest_assessment.total_score)}/100`
                                : 'Chua co diem'}
                            </strong>
                          </div>
                        </div>

                        <div className="study-dashboard__project-grid">
                          <section className="study-dashboard__project-panel">
                            <div className="study-dashboard__panel-headline">
                              <div>
                                <span className="study-dashboard__section-kicker">Tien do hoc</span>
                                <h4>{project.progress_percentage}% hoan thanh</h4>
                              </div>
                              <Target size={18} />
                            </div>

                            <div className="study-dashboard__progress-track" aria-hidden="true">
                              <div
                                className="study-dashboard__progress-fill"
                                style={{ width: `${project.progress_percentage}%` }}
                              />
                            </div>

                            <div className="study-dashboard__stats-row">
                              <div className="study-dashboard__mini-stat">
                                <strong>{project.assignments_completed}</strong>
                                <span>Bai da nop</span>
                              </div>
                              <div className="study-dashboard__mini-stat">
                                <strong>{project.assignments_pending}</strong>
                                <span>Bai con lai</span>
                              </div>
                              <div className="study-dashboard__mini-stat">
                                <strong>{project.materials_count}</strong>
                                <span>Tai lieu</span>
                              </div>
                              <div className="study-dashboard__mini-stat">
                                <strong>{project.submissions_total}</strong>
                                <span>Luot nop</span>
                              </div>
                            </div>
                          </section>

                          <section className="study-dashboard__project-panel">
                            <div className="study-dashboard__panel-headline">
                              <div>
                                <span className="study-dashboard__section-kicker">Tu danh gia</span>
                                <h4>{readinessMeta.description}</h4>
                              </div>
                              <Brain size={18} />
                            </div>

                            <div className="study-dashboard__assessment-meta">
                              <span>
                                <Clock3 size={15} />
                                Cap nhat: {formatDateTime(project.latest_assessment?.created_at)}
                              </span>
                            </div>

                            <div className="study-dashboard__insight-block">
                              <p>
                                {project.latest_assessment?.analysis_text ??
                                  'Chua co nhan dinh AI cho project nay. Nen thuc hien bai tu danh gia de lay muc do san sang.'}
                              </p>
                            </div>

                            <div className="study-dashboard__hint">
                              <Sparkles size={16} />
                              <span>
                                {project.latest_assessment?.recommendations ?? project.next_action}
                              </span>
                            </div>
                          </section>
                        </div>

                        <section className="study-dashboard__assignments">
                          <div className="study-dashboard__panel-headline">
                            <div>
                              <span className="study-dashboard__section-kicker">Bai tap va bai kiem tra</span>
                              <h4>Nhung dau viec gan nhat trong project</h4>
                            </div>
                            <BookOpen size={18} />
                          </div>

                          {project.recent_assignments.length === 0 ? (
                            <div className="study-dashboard__empty-inline">
                              <FileText size={18} />
                              <span>Project nay chua co assignment nao de hien thi.</span>
                            </div>
                          ) : (
                            <div className="study-dashboard__assignment-list">
                              {project.recent_assignments.map((assignment) => {
                                const assignmentState = getAssignmentState(assignment);

                                return (
                                  <article key={assignment.id} className="study-dashboard__assignment-item">
                                    <div className="study-dashboard__assignment-copy">
                                      <div className="study-dashboard__assignment-top">
                                        <h5>{assignment.title}</h5>
                                        <span
                                          className={`study-dashboard__pill study-dashboard__pill--${assignmentState.tone}`}
                                        >
                                          {assignmentState.label}
                                        </span>
                                      </div>
                                      <p>
                                        {assignment.description?.trim()
                                          ? assignment.description
                                          : 'Chua co mo ta cho bai tap nay.'}
                                      </p>
                                    </div>

                                    <div className="study-dashboard__assignment-side">
                                      <span>
                                        <Clock3 size={15} />
                                        Tao luc {formatShortDate(assignment.created_at)}
                                      </span>
                                      <span>
                                        <ArrowRight size={15} />
                                        {assignment.last_submitted_at
                                          ? `Lan nop gan nhat ${formatShortDate(assignment.last_submitted_at)}`
                                          : 'Chua co submission'}
                                      </span>
                                      <span>
                                        <CheckCircle2 size={15} />
                                        {assignment.submission_count} luot nop bai
                                      </span>
                                    </div>
                                  </article>
                                );
                              })}
                            </div>
                          )}
                        </section>

                        <div className="study-dashboard__next-step">
                          <Sparkles size={18} />
                          <div>
                            <strong>Buoc uu tien tiep theo</strong>
                            <p>{project.next_action}</p>
                          </div>
                        </div>
                      </article>
                    );
                  })}
                </div>
              )}
            </section>
          </div>

          <aside className="study-dashboard__side">
            <section className="study-dashboard__section-card">
              <div className="study-dashboard__section-head">
                <div>
                  <span className="study-dashboard__section-kicker">Create project</span>
                  <h2>Tao project moi</h2>
                </div>
                <Plus size={20} />
              </div>

              <p className="study-dashboard__section-copy">
                Khi ban bat dau mot huong hoc moi hoac mot de tai moi, tao project tai day de
                sau do gan bai tap, tu danh gia va theo doi tien do tren dashboard.
              </p>

              {createProjectStatus ? (
                <div className="study-dashboard__banner study-dashboard__banner--success">
                  <CheckCircle2 size={18} />
                  <span>{createProjectStatus}</span>
                </div>
              ) : null}

              {createProjectError ? (
                <div className="study-dashboard__banner study-dashboard__banner--error">
                  <CircleAlert size={18} />
                  <span>{createProjectError}</span>
                </div>
              ) : null}

              {isCreateOpen ? (
                <div className="study-dashboard__create-form">
                  <div className="study-dashboard__field">
                    <label htmlFor="project-name">Ten project</label>
                    <input
                      id="project-name"
                      type="text"
                      value={projectName}
                      onChange={(event) => setProjectName(event.target.value)}
                      placeholder="Vi du: AI Readiness - Ky nang tu hoc"
                    />
                  </div>

                  <div className="study-dashboard__field">
                    <label htmlFor="project-description">Mo ta ngan</label>
                    <textarea
                      id="project-description"
                      value={projectDescription}
                      onChange={(event) => setProjectDescription(event.target.value)}
                      placeholder="Mo ta muc tieu, noi dung hoc, hoac nhom ky nang ban muon theo doi."
                      rows={4}
                    />
                  </div>

                  <div className="study-dashboard__create-actions">
                    <button
                      className="study-dashboard__primary-link study-dashboard__primary-link--button"
                      type="button"
                      onClick={handleCreateProject}
                      disabled={isCreatingProject}
                    >
                      <Plus size={18} />
                      {isCreatingProject ? 'Dang tao...' : 'Xac nhan tao project'}
                    </button>
                    <button
                      className="study-dashboard__ghost-link study-dashboard__ghost-link--button"
                      type="button"
                      onClick={() => {
                        setIsCreateOpen(false);
                        resetCreateProjectForm();
                      }}
                      disabled={isCreatingProject}
                    >
                      Huy
                    </button>
                  </div>
                </div>
              ) : (
                <button
                  className="study-dashboard__create-toggle"
                  type="button"
                  onClick={() => {
                    setIsCreateOpen(true);
                    setCreateProjectStatus('');
                    setCreateProjectError('');
                  }}
                >
                  <Plus size={18} />
                  Mo form tao project
                </button>
              )}
            </section>

            <section className="study-dashboard__section-card study-dashboard__section-card--accent">
              <div className="study-dashboard__section-head study-dashboard__section-head--light">
                <div>
                  <span className="study-dashboard__section-kicker study-dashboard__section-kicker--light">
                    Priorities
                  </span>
                  <h2>Nhung viec nen xu ly truoc</h2>
                </div>
                <Sparkles size={20} />
              </div>

              {topPriorities.length === 0 ? (
                <div className="study-dashboard__empty-inline study-dashboard__empty-inline--light">
                  <CheckCircle2 size={18} />
                  <span>Chua co uu tien nao noi bat. Dashboard se cap nhat khi co du lieu moi.</span>
                </div>
              ) : (
                <div className="study-dashboard__priority-list">
                  {topPriorities.map((project) => (
                    <article key={project.id} className="study-dashboard__priority-item">
                      <div>
                        <span className="study-dashboard__priority-label">{project.name}</span>
                        <strong>
                          {project.latest_assessment
                            ? getReadinessMeta(project.latest_assessment.readiness_level).label
                            : 'Can tu danh gia'}
                        </strong>
                        <p>{project.next_action}</p>
                      </div>
                      <ArrowRight size={18} />
                    </article>
                  ))}
                </div>
              )}
            </section>

            <section className="study-dashboard__section-card">
              <div className="study-dashboard__section-head">
                <div>
                  <span className="study-dashboard__section-kicker">How to read</span>
                  <h2>Dashboard nay cho ban biet gi</h2>
                </div>
                <Brain size={20} />
              </div>

              <div className="study-dashboard__info-list">
                <article className="study-dashboard__info-item">
                  <TrendingUp size={18} />
                  <div>
                    <strong>Tien do hoc</strong>
                    <p>Duoc tinh tu so bai tap da nop tren tong assignment cua tung project.</p>
                  </div>
                </article>
                <article className="study-dashboard__info-item">
                  <Brain size={18} />
                  <div>
                    <strong>Readiness assessment</strong>
                    <p>Cho biet muc do san sang hoc tap va thuc hien project tai thoi diem hien tai.</p>
                  </div>
                </article>
                <article className="study-dashboard__info-item">
                  <Sparkles size={18} />
                  <div>
                    <strong>Goi y AI</strong>
                    <p>Tom tat diem can uu tien de ban biet nen hoc tiep theo huong nao.</p>
                  </div>
                </article>
              </div>
            </section>
          </aside>
        </section>
      </div>
    </main>
  );
}
