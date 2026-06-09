import { useEffect, useState } from 'react';
import {
  ArrowRight,
  Brain,
  CheckCircle2,
  CircleAlert,
  Clock3,
  FolderKanban,
  GraduationCap,
  LayoutDashboard,
  Plus,
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

type CreatedProject = {
  id: string;
  name: string;
  description?: string | null;
};

type CurrentSubscription = {
  id: string;
  user_id: string;
  plan_id: string;
  plan_name?: string|null;
  is_active: boolean;
  start_date: string| null;
  end_date: string|null;
};

const getDisplayName = (accountName?: string | null, email?: string | null) => {
  if (accountName?.trim()) {
    return accountName.trim();
  }

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

const getAvatarInitials = (name?: string | null, email?: string | null) => {
  const source = name?.trim() || email?.trim() || 'U';
  const chunks = source.includes('@')
    ? [source.charAt(0)]
    : source.split(/\s+/).filter(Boolean).slice(0, 2);

  return (
    chunks
      .map((chunk) => chunk.charAt(0).toUpperCase())
      .join('') || 'U'
  );
};

const formatDateTime = (value?: string | null) => {
  if (!value) {
    return 'Chưa có dữ liệu';
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return 'Chưa có dữ liệu';
  }

  return parsed.toLocaleString('vi-VN', {
    hour: '2-digit',
    minute: '2-digit',
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
        description: 'Đang có nền tảng, nhưng cần giảm các điểm yếu hiện tại.',
      };
    case 'low':
      return {
        label: 'Can cuong co',
        tone: 'low' as const,
        description: 'Nên ưu tiên kiến thức nền và lặp lại nhịp học ổn định.',
      };
    default:
      return {
        label: 'Chưa đánh giá',
        tone: 'empty' as const,
        description: 'Bạn chưa có kết quả tự đánh giá cho dự án này.',
      };
  }
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

  return 'Không tải được dashboard. Vui lòng thử lại.';
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

  return 'Không tạo được dự án. Vui lòng thử lại.';
};

const validateProjectInput = (payload: CreateProjectPayload) => {
  if (!payload.name.trim()) {
    return 'Vui lòng nhập tên dự án.';
  }

  if (payload.name.trim().length < 3) {
    return 'Tên dự án phải có ít nhất 3 ký tự.';
  }

  return null;
};

const loadDashboardOverview = async () => {
  const response = await api.get<DashboardOverview>('/projects/overview');
  return response.data;
};

export function DashboardPage() {
  const navigate = useNavigate();
  const { user } = useAuth();

  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isCreatingProject, setIsCreatingProject] = useState(false);
  const [createProjectError, setCreateProjectError] = useState('');
  const [createProjectStatus, setCreateProjectStatus] = useState('');
  const [projectName, setProjectName] = useState('');
  const [projectDescription, setProjectDescription] = useState('');
  const [subscription, setsubscription] = useState<CurrentSubscription | null>(null);

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
        }
      }
    };

    void loadOverview();

    return () => {
      isMounted = false;
    };
  }, []);

  const fetchSubscription = async () =>{
    try{
      setIsLoading(true);
      setError("");
      const respont = await api.get<CurrentSubscription | null>("/pricing-plans/subscriptions/me/current",);
      setsubscription(respont.data);
    }catch{
      setError("không thể kiểm tra gói dịch vụ hiện tại");
      setsubscription(null);
    }finally{
      setIsLoading(false);
    }
  };

  useEffect(() =>{
    fetchSubscription();
  },[]);

  const hasActiveSubscription = Boolean(subscription?.is_active);

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
      const createResponse = await api.post<CreatedProject>('/projects', payload);
      const response = await loadDashboardOverview();
      setOverview(response);
      setCreateProjectStatus('Đã tạo dự án mới thành công.');
      resetCreateProjectForm();
      setIsCreateOpen(false);
      setError('');
      navigate(`/projects/${createResponse.data.id}`);
    } catch (createError) {
      setCreateProjectError(getCreateProjectErrorMessage(createError));
    } finally {
      setIsCreatingProject(false);
    }
  };

  const displayName = getDisplayName(user?.account_name, user?.email);
  const avatarInitials = getAvatarInitials(displayName, user?.email);
  const projects = overview?.projects ?? [];
  const summary = overview?.summary;
  const topPriorities = [...projects]
    .sort((left, right) => getPriorityRank(left) - getPriorityRank(right))
    .slice(0, 3);

  const summaryCards: SummaryCard[] = [
    {
      label: 'Dự án đang theo học',
      value: String(summary?.total_projects ?? 0),
      detail: 'Tổng số dự án bạn đang có liên quan trong hệ thống.',
      icon: FolderKanban,
      tone: 'blue',
    },
    {
      label: 'Tiến độ trung bình',
      value: `${summary?.average_progress ?? 0}%`,
      detail: 'Tỷ lệ bài tập đã nộp trên tổng số bài tập được theo dõi.',
      icon: TrendingUp,
      tone: 'teal',
    },
    {
      label: 'Bài tập đã nộp',
      value: `${summary?.submitted_assignments ?? 0}/${summary?.tracked_assignments ?? 0}`,
      detail: 'Mức độ hoàn thành bài tập trên tất cả dự án của bạn.',
      icon: CheckCircle2,
      tone: 'amber',
    },
    {
      label: 'Lần tự đánh giá',
      value: String(summary?.assessments_completed ?? 0),
      detail: 'Số dự án đã có kết quả đánh giá mức độ sẵn sàng học tập.',
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
            <span className="study-dashboard__kicker">Không gian học tập</span>
            {hasActiveSubscription?(
              <h1>Bảng điều khiển</h1>
            ): (
              <Link className='upgrade' to="/upgrade">Nâng cấp</Link>
            )}
          </div>

          <div className="study-dashboard__bar-actions">
            {user?.is_superuser ? (
              <Link className="study-dashboard__admin-link" to="/admin">
                <ShieldCheck size={16} />
                Admin
              </Link>
            ) : null}
            <Link className="study-dashboard__account-link" to="/profile">
              <span className="study-dashboard__account-avatar">{avatarInitials}</span>
              <span className="study-dashboard__account-copy">
                <strong>{displayName}</strong>
                <span>{user?.email ?? 'Không có email'}</span>
              </span>
            </Link>
          </div>
        </header>

        <section className="study-dashboard__hero">
          <div className="study-dashboard__hero-main">
            <div className="study-dashboard__hero-head">
              <span className="study-dashboard__eyebrow">Tổng quan</span>
              <h2>Tổng quan học tập</h2>
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
        </section>

        <section className="study-dashboard__content">
          <div className="study-dashboard__main">
            <section className="study-dashboard__section-card">
              <div className="study-dashboard__section-head">
                <Link to="/projects" className="project-section__link">
                  <span className="study-dashboard__section-kicker">Dự án</span>
                  <h2 style={{color:'black'}}>Các dự án đang theo học</h2>
                </Link>
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
                    <h3>Chưa có dự án nào để theo dõi</h3>
                    <p>
                      Khi bạn có dự án, bài tập, lượt nộp hoặc kết quả tự đánh giá, bảng điều khiển
                      này sẽ tự động tổng hợp để hiển thị tiến độ học tập.
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
                                Dự án
                              </span>
                              <span className="study-dashboard__pill study-dashboard__pill--neutral">
                                <UserRound size={14} />
                                {project.is_owner ? 'Sở hữu' : 'Đang tham gia'}
                              </span>
                            </div>
                            <Link to={`/projects/${project.id}`} className="study-dashboard__project-link">
                              <h3>{project.name}</h3>
                              <p>
                                {project.description?.trim()
                                  ? project.description
                                  : 'Dự án chưa có mô tả. Bảng điều khiển vẫn theo dõi bài tập, lượt nộp và kết quả đánh giá của bạn.'}
                              </p>
                            </Link>
                          </div>

                          <div className={`study-dashboard__readiness study-dashboard__readiness--${readinessMeta.tone}`}>
                            <span>{readinessMeta.label}</span>
                            <strong>
                              {project.latest_assessment?.total_score != null
                                ? `${Math.round(project.latest_assessment.total_score)}/100`
                                : 'Chưa có điểm'}
                            </strong>
                          </div>
                        </div>

                        <div className="study-dashboard__project-grid">
                          <section className="study-dashboard__project-panel">
                            <div className="study-dashboard__panel-headline">
                              <div>
                                <span className="study-dashboard__section-kicker">Tiến độ học</span>
                                <h4>{project.progress_percentage}% hoàn thành</h4>
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
                                <span>Bài đã nộp</span>
                              </div>
                              <div className="study-dashboard__mini-stat">
                                <strong>{project.assignments_pending}</strong>
                                <span>Bài còn lại</span>
                              </div>
                              <div className="study-dashboard__mini-stat">
                                <strong>{project.materials_count}</strong>
                                <span>Tài liệu</span>
                              </div>
                              <div className="study-dashboard__mini-stat">
                                <strong>{project.submissions_total}</strong>
                                <span>Lượt nộp</span>
                              </div>
                            </div>
                          </section>

                          <section className="study-dashboard__project-panel">
                            <div className="study-dashboard__panel-headline">
                              <div>
                                <span className="study-dashboard__section-kicker">Tự đánh giá</span>
                                <h4>{readinessMeta.description}</h4>
                              </div>
                              <Brain size={18} />
                            </div>

                            <div className="study-dashboard__assessment-meta">
                              <span>
                                <Clock3 size={15} />
                                Cập nhật: {formatDateTime(project.latest_assessment?.created_at)}
                              </span>
                            </div>

                            <div className="study-dashboard__insight-block">
                              <p>
                                {project.latest_assessment?.analysis_text ??
                                  'Chưa có nhận định cho dự án này. Cần thực hiện bài tự đánh giá để lấy mức độ sẵn sàng.'}
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

                        <div className="study-dashboard__next-step">
                          <Sparkles size={18} />
                          <div>
                            <strong>Bước ưu tiên tiếp theo</strong>
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
                  <span className="study-dashboard__section-kicker">Tạo dự án</span>
                  <h2>Tạo dự án mới</h2>
                </div>
                <Plus size={20} />
              </div>

              <p className="study-dashboard__section-copy">
                Khi bạn bắt đầu một hướng học mới hoặc một đề tài mới, tạo dự án tại đây để
                sau đó gắn bài tập, tự đánh giá và theo dõi tiến độ trên bảng điều khiển.
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
                    <label htmlFor="project-name">Tên dự án</label>
                    <input
                      id="project-name"
                      type="text"
                      value={projectName}
                      onChange={(event) => setProjectName(event.target.value)}
                      placeholder="Ví dụ: Kỹ năng tự học"
                    />
                  </div>

                  <div className="study-dashboard__field">
                    <label htmlFor="project-description">Mô tả ngắn</label>
                    <textarea
                      id="project-description"
                      value={projectDescription}
                      onChange={(event) => setProjectDescription(event.target.value)}
                      placeholder="Mô tả mục tiêu, nội dung học, hoặc nhóm kỹ năng bạn muốn theo dõi."
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
                      {isCreatingProject ? 'Đang tạo...' : 'Xác nhận tạo dự án'}
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
                      Hủy
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
                  Mở biểu mẫu tạo dự án
                </button>
              )}
            </section>

            <section className="study-dashboard__section-card study-dashboard__section-card--accent">
              <div className="study-dashboard__section-head study-dashboard__section-head--light">
                <div>
                  <span className="study-dashboard__section-kicker study-dashboard__section-kicker--light">
                    Priorities
                  </span>
                  <h2>Những việc nên xử lý trước</h2>
                </div>

              </div>

              {topPriorities.length === 0 ? (
                <div className="study-dashboard__empty-inline study-dashboard__empty-inline--light">
                  <CheckCircle2 size={18} />
                  <span>Chưa có ưu tiên nào nổi bật. Bảng điều khiển sẽ cập nhật khi có dữ liệu mới.</span>
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
                            : 'Cần tự đánh giá'}
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
                  <span className="study-dashboard__section-kicker">Cách đọc</span>
                  <h2>Bảng điều khiển này cho bạn biết gì</h2>
                </div>

              </div>

              <div className="study-dashboard__info-list">
                <article className="study-dashboard__info-item">
                  <TrendingUp size={18} />
                  <div>
                    <strong>Tiến độ học</strong>
                    <p>Được tính từ số bài tập đã nộp trên tổng bài tập của từng dự án.</p>
                  </div>
                </article>
                <article className="study-dashboard__info-item">
                  <Brain size={18} />
                  <div>
                    <strong>Tự đánh giá mức độ sẵn sàng</strong>
                    <p>Cho biết mức độ sẵn sàng học tập và thực hiện dự án tại thời điểm hiện tại.</p>
                  </div>
                </article>
                <article className="study-dashboard__info-item">
                  <Sparkles size={18} />
                  <div>
                    <strong>Gợi ý học tập</strong>
                    <p>Tóm tắt điểm cần ưu tiên để bạn biết nên học tiếp theo hướng nào.</p>
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
