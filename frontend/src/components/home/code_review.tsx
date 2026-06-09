import { useCallback, useEffect, useMemo, useState } from "react";
import axios from "axios";
import { Link, useParams } from "react-router-dom";
import {
  ArrowLeft,
  CircleAlert,
  Clock3,
  Github,
  GitPullRequestArrow,
  Loader2,
  RotateCcw,
  Sparkles,
  Upload,
} from "lucide-react";

import { api } from "@/api/axios";
import GithubModal from "./githubmodal";
import "./lession.css";

type Assignment = {
  id: string;
  project_id?: string | null;
  title: string;
  description?: string | null;
};

type ProjectInfo = {
  id: string;
  name: string;
  description?: string | null;
};

type CodeSubmission = {
  id: string;
  assignment_id: string;
  user_id?: string;
  github_repo_url: string;
  file_path?: string | null;
  commit_hash?: string | null;
  score?: number | null;
  status?: string | null;
  submitted_at?: string | null;
  graded_at?: string | null;
  feedback?: RawFeedback;
};

type CodeFeedback = {
  id: string;
  overview: string;
  flow_analysis?: string | null;
  code_quality_score?: number | null;
  logic_score?: number | null;
  performance_score?: number | null;
  strengths?: string | null;
  weaknesses?: string | null;
  improvement_suggestions?: string | null;
};

type RawFeedback = CodeFeedback | string | Record<string, unknown> | null | undefined;

type SubmissionDetail = {
  submission: CodeSubmission;
  feedback?: RawFeedback;
};

type SubmissionDetailResponse = SubmissionDetail | CodeFeedback | string | Record<string, unknown>;

const statusLabels: Record<string, string> = {
  submitted: "Chưa chấm",
  grading: "Đang chấm",
  graded: "Đã chấm",
  failed: "Chưa chấm",
};

const feedbackFields = [
  "overview",
  "flow_analysis",
  "code_quality_score",
  "logic_score",
  "performance_score",
  "strengths",
  "weaknesses",
  "improvement_suggestions",
] as const;

const textFeedbackFields = [
  "overview",
  "flow_analysis",
  "strengths",
  "weaknesses",
  "improvement_suggestions",
] as const;

const scoreFeedbackFields = [
  "code_quality_score",
  "logic_score",
  "performance_score",
] as const;

const feedbackFieldPattern = feedbackFields.join("|");

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function stripJsonFence(value: string) {
  const trimmed = value.trim();
  if (!trimmed.startsWith("```")) {
    return trimmed;
  }

  const lines = trimmed.split(/\r?\n/);
  if (lines[0]?.trim().startsWith("```")) {
    lines.shift();
  }
  if (lines[lines.length - 1]?.trim().startsWith("```")) {
    lines.pop();
  }
  return lines.join("\n").trim();
}

function parseJsonObject(value: unknown): Record<string, unknown> | null {
  if (isRecord(value)) {
    return value;
  }
  if (typeof value !== "string") {
    return null;
  }

  let candidate: unknown = stripJsonFence(value);

  for (let attempt = 0; attempt < 3; attempt += 1) {
    if (isRecord(candidate)) {
      return candidate;
    }
    if (typeof candidate !== "string") {
      return null;
    }

    let trimmed = stripJsonFence(candidate);
    const jsonStart = trimmed.indexOf("{");
    const jsonEnd = trimmed.lastIndexOf("}");
    if (jsonStart !== -1 && jsonEnd > jsonStart) {
      trimmed = trimmed.slice(jsonStart, jsonEnd + 1);
    }

    const startsAsObject = trimmed.startsWith("{") && trimmed.endsWith("}");
    const startsAsQuotedJson = trimmed.startsWith('"') && trimmed.endsWith('"');
    if (!startsAsObject && !startsAsQuotedJson) {
      return null;
    }

    try {
      candidate = JSON.parse(trimmed);
    } catch {
      return null;
    }
  }

  return isRecord(candidate) ? candidate : null;
}

function cleanLooseJsonText(value: string) {
  let cleaned = value.trim().replace(/,$/, "").trim();
  if (cleaned.startsWith('"') && cleaned.endsWith('"')) {
    try {
      const parsed = JSON.parse(cleaned);
      return typeof parsed === "string" ? parsed.trim() : String(parsed).trim();
    } catch {
      cleaned = cleaned.slice(1, -1);
    }
  }

  return cleaned
    .replace(/\\"/g, '"')
    .replace(/\\n/g, "\n")
    .replace(/\\r/g, "\r")
    .replace(/\\t/g, "\t")
    .trim();
}

function parseLooseFeedbackObject(value: unknown): Record<string, unknown> | null {
  if (typeof value !== "string") {
    return null;
  }

  let candidate = stripJsonFence(value);
  const jsonStart = candidate.indexOf("{");
  const jsonEnd = candidate.lastIndexOf("}");
  if (jsonStart !== -1 && jsonEnd > jsonStart) {
    candidate = candidate.slice(jsonStart, jsonEnd + 1);
  }

  if (!feedbackFields.some((field) => candidate.includes(`"${field}"`))) {
    return null;
  }

  const result: Record<string, unknown> = {};

  textFeedbackFields.forEach((field) => {
    const pattern = new RegExp(
      `"${field}"\\s*:\\s*([\\s\\S]*?)(?=,\\s*"(?:${feedbackFieldPattern})"\\s*:|\\s*}\\s*$)`,
    );
    const match = candidate.match(pattern);
    if (match?.[1]) {
      result[field] = cleanLooseJsonText(match[1]);
    }
  });

  scoreFeedbackFields.forEach((field) => {
    const pattern = new RegExp(`"${field}"\\s*:\\s*"?(-?\\d+(?:\\.\\d+)?)"?`);
    const match = candidate.match(pattern);
    if (match?.[1]) {
      const score = Number(match[1]);
      if (Number.isFinite(score)) {
        result[field] = score;
      }
    }
  });

  return Object.keys(result).length > 0 ? result : null;
}

function parseFeedbackPayload(value: unknown): Record<string, unknown> | null {
  return parseJsonObject(value) ?? parseLooseFeedbackObject(value);
}

function getTextField(source: Record<string, unknown>, key: keyof CodeFeedback) {
  const value = source[key];
  if (typeof value === "string") {
    const parsed = parseFeedbackPayload(value);
    if (parsed && feedbackFields.some((field) => field in parsed)) {
      return getTextField(parsed, key);
    }
    if (feedbackFields.some((field) => value.includes(`"${field}"`))) {
      return null;
    }
    return value;
  }
  if (Array.isArray(value)) {
    return value.map((item) => String(item)).join("\n");
  }
  return null;
}

function getNumberField(source: Record<string, unknown>, key: keyof CodeFeedback) {
  const value = source[key];
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function normalizeFeedback(rawFeedback?: RawFeedback): CodeFeedback | null {
  const base = parseFeedbackPayload(rawFeedback);
  if (!base) {
    return null;
  }

  const feedbackPayload = parseFeedbackPayload(base.feedback);
  if (feedbackPayload && feedbackFields.some((field) => field in feedbackPayload)) {
    return normalizeFeedback(feedbackPayload);
  }

  const overviewPayload = parseFeedbackPayload(base.overview);
  const source =
    overviewPayload && feedbackFields.some((field) => field in overviewPayload)
      ? { ...base, ...overviewPayload, id: base.id }
      : base;

  return {
    id: String(source.id ?? ""),
    overview: getTextField(source, "overview") ?? "",
    flow_analysis: getTextField(source, "flow_analysis"),
    code_quality_score: getNumberField(source, "code_quality_score"),
    logic_score: getNumberField(source, "logic_score"),
    performance_score: getNumberField(source, "performance_score"),
    strengths: getTextField(source, "strengths"),
    weaknesses: getTextField(source, "weaknesses"),
    improvement_suggestions: getTextField(source, "improvement_suggestions"),
  };
}

function normalizeSubmissionDetail(
  responseData: SubmissionDetailResponse,
  fallbackSubmission?: CodeSubmission | null,
): SubmissionDetail | null {
  if (!isRecord(responseData)) {
    return fallbackSubmission ? { submission: fallbackSubmission, feedback: responseData } : null;
  }

  const responseRecord = responseData as Record<string, unknown>;
  if (isRecord(responseRecord.submission)) {
    const nestedFeedback = responseRecord.feedback as RawFeedback;
    const nestedSubmission = {
      ...(responseRecord.submission as CodeSubmission),
      feedback:
        (responseRecord.submission as CodeSubmission).feedback ?? nestedFeedback ?? null,
    };
    return {
      submission: nestedSubmission,
      feedback: nestedSubmission.feedback,
    };
  }

  if ("submission_id" in responseRecord && fallbackSubmission) {
    return {
      submission: fallbackSubmission,
      feedback: responseData,
    };
  }

  if ("id" in responseRecord) {
    const flatSubmission = responseRecord as CodeSubmission;
    return {
      submission: flatSubmission,
      feedback: flatSubmission.feedback ?? null,
    };
  }

  return fallbackSubmission ? { submission: fallbackSubmission, feedback: responseData } : null;
}

function formatDate(value?: string | null) {
  if (!value) {
    return "-";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "-";
  }

  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(date);
}

function formatScore(value?: number | null) {
  if (value === null || value === undefined) {
    return "-";
  }

  return value.toFixed(1);
}

function getDisplayStatus(submission?: CodeSubmission | null, hasFeedback = false) {
  if (!submission) {
    return "Chưa nộp";
  }
  if (hasFeedback || (submission.score !== null && submission.score !== undefined)) {
    return statusLabels.graded;
  }
  return statusLabels[submission.status ?? ""] ?? "Chưa chấm";
}

export default function CodeReview() {
  const { moduleId } = useParams();

  const [assignment, setAssignment] = useState<Assignment | null>(null);
  const [project, setProject] = useState<ProjectInfo | null>(null);
  const [submissions, setSubmissions] = useState<CodeSubmission[]>([]);
  const [selectedDetail, setSelectedDetail] = useState<SubmissionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const latestSubmission = submissions[0] ?? null;
  const selectedSubmission = selectedDetail?.submission ?? latestSubmission;
  const rawFeedback =
    selectedDetail !== null
      ? selectedDetail.submission.feedback ?? selectedDetail.feedback ?? null
      : latestSubmission?.feedback ?? null;
  const parsedFeedback = useMemo(() => normalizeFeedback(rawFeedback), [rawFeedback]);
  const feedback = parsedFeedback;
  const score = selectedDetail?.submission.score ?? latestSubmission?.score ?? null;
  const canRetryGrading = Boolean(
    selectedSubmission &&
      !detailLoading &&
      (Boolean(feedback) ||
        selectedSubmission.score != null ||
        ["failed", "grading"].includes(selectedSubmission.status ?? "")),
  );

  const totalScore = useMemo(() => {
    if (feedback) {
      return (
        (feedback.code_quality_score ?? 0) +
        (feedback.logic_score ?? 0) +
        (feedback.performance_score ?? 0)
      ) / 3;
    }

    return score;
  }, [feedback, score]);
  const backToProjectLink =
    project?.id ?? assignment?.project_id
      ? `/projects/${project?.id ?? assignment?.project_id}`
      : "/projects";

  const loadDetail = useCallback(async (
    submissionId: string,
    fallbackSubmission?: CodeSubmission | null,
  ) => {
    setDetailLoading(true);
    try {
      const response = await api.get<SubmissionDetailResponse>(
        `/code-submissions/${submissionId}`,
      );
      const detail = normalizeSubmissionDetail(response.data, fallbackSubmission ?? null);

      if (detail?.feedback) {
        setSelectedDetail(detail);
        return;
      }

      try {
        const feedbackResponse = await api.get<RawFeedback>(
          `/ai-code-feedback/submission/${submissionId}`,
        );
        const mergedSubmission = detail?.submission ?? fallbackSubmission ?? null;
        setSelectedDetail(
          mergedSubmission
            ? {
                submission: {
                  ...mergedSubmission,
                  feedback: feedbackResponse.data,
                },
                feedback: feedbackResponse.data,
              }
              : null,
        );
      } catch {
        setSelectedDetail(detail);
      }
    } catch {
      setSelectedDetail(null);
    } finally {
      setDetailLoading(false);
    }
  }, []);

  const loadCodeReview = useCallback(async () => {
    if (!moduleId) {
      setAssignment(null);
      setProject(null);
      setSubmissions([]);
      setSelectedDetail(null);
      setError("Không tìm thấy bài học.");
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    setNotice(null);

    try {
      const assignmentResponse = await api.get<Assignment>(
        `/assignments/modules/${moduleId}/assignment`,
      );
      const currentAssignment = assignmentResponse.data;
      let currentProject: ProjectInfo | null = null;
      if (currentAssignment.project_id) {
        try {
          const projectResponse = await api.get<ProjectInfo>(
            `/projects/${currentAssignment.project_id}`,
          );
          currentProject = projectResponse.data;
        } catch {
          currentProject = null;
        }
      }
      const historyResponse = await api.get<CodeSubmission[]>(
        `/code-submissions/history/${currentAssignment.id}`,
      );
      setAssignment(currentAssignment);
      setProject(currentProject);
      setSubmissions(historyResponse.data);

      const firstSubmission = historyResponse.data[0];
      if (firstSubmission) {
        await loadDetail(firstSubmission.id, firstSubmission);
      } else {
        setSelectedDetail(null);
      }
    } catch (loadError) {
      setAssignment(null);
      setProject(null);
      setSubmissions([]);
      setSelectedDetail(null);

      if (axios.isAxiosError(loadError) && loadError.response?.status === 404) {
        setError("Bài học này chưa có bài tập code để nộp GitHub.");
      } else {
        setError("Không thể tải dữ liệu code review.");
      }
    } finally {
      setLoading(false);
    }
  }, [loadDetail, moduleId]);

  useEffect(() => {
    void loadCodeReview();
  }, [loadCodeReview]);

  const retryGrading = useCallback(async () => {
    if (!selectedSubmission) {
      return;
    }

    setDetailLoading(true);
    setError(null);
    setNotice(null);
    try {
      const response = await api.post<CodeSubmission>(
        `/code-submissions/${selectedSubmission.id}/retry`,
      );
      setNotice("Đã gửi yêu cầu chấm lại. Kết quả sẽ cập nhật sau khi hệ thống chấm xong.");
      await loadCodeReview();
      await loadDetail(response.data.id, response.data);
    } catch {
      setError("Chấm lại chưa thành công. Kiểm tra link GitHub hoặc thử lại sau.");
    } finally {
      setDetailLoading(false);
    }
  }, [loadCodeReview, loadDetail, selectedSubmission]);

  return (
    <>
      <main className="lession">
        <div className="lession-banner lession-banner--a" />
        <div className="lession-banner lession-banner--b" />
        <div className="lession-banner lession-banner--c" />

        <section className="lession-header">
          <header className="lession-header__title">
            <div className="lession-header__copy">
              <p className="lession-detail__eyebrow">Đánh giá mã nguồn</p>
              <h2 className="lession-header__heading">
                {project?.name ?? assignment?.title ?? "Nộp link GitHub"}
              </h2>
              <p className="lession-header__description">
                {project?.description ?? assignment?.description ??
                  "Nộp kho GitHub để hệ thống đọc mã nguồn, chấm điểm và trả nhận xét."}
              </p>
            </div>

            <div className="lession-header__button">
              <Link className="lession-header__button--add" to={backToProjectLink}>
                <ArrowLeft size={16} />
                Bài học
              </Link>
              <button
                className="lession-header__button--add"
                type="button"
                onClick={() => setOpen(true)}
                disabled={!assignment || loading}
              >
                <Upload size={16} />
                Nộp GitHub
              </button>
              {canRetryGrading ? (
                <button
                  className="lession-header__button--add"
                  type="button"
                  onClick={() => void retryGrading()}
                  disabled={detailLoading}
                >
                  {detailLoading ? (
                    <Loader2 size={16} className="github-modal__spinner" />
                  ) : (
                    <RotateCcw size={16} />
                  )}
                  Chấm lại
                </button>
              ) : null}
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
                  <span>Đang tải lịch sử nộp bài...</span>
                </div>
              ) : submissions.length === 0 ? (
                <div className="code-review-empty">
                  <Github size={22} />
                  <strong>Chưa có lần nộp nào</strong>
                  <span>Hãy nộp kho GitHub để hệ thống bắt đầu chấm mã nguồn.</span>
                </div>
              ) : (
                <div className="code-review-feedback">
                  <div className="code-review-feedback__head">
                    <div>
                      <span>Kết quả mới nhất</span>
                      <strong>{formatScore(totalScore)}</strong>
                    </div>
                    {detailLoading ? <Loader2 size={18} className="github-modal__spinner" /> : null}
                  </div>

                  {feedback ? (
                    <div className="code-review-feedback__grid">
                      <article className="code-review-feedback__block code-review-feedback__block--wide">
                        <h3>Tổng quan</h3>
                        <p>{feedback.overview || "Chưa có dữ liệu."}</p>
                      </article>
                      <article className="code-review-feedback__block">
                        <h3>Chất lượng code</h3>
                        <p>{formatScore(feedback.code_quality_score)}</p>
                      </article>
                      <article className="code-review-feedback__block">
                        <h3>Logic</h3>
                        <p>{formatScore(feedback.logic_score)}</p>
                      </article>
                      <article className="code-review-feedback__block">
                        <h3>Hiệu năng</h3>
                        <p>{formatScore(feedback.performance_score)}</p>
                      </article>
                      <article className="code-review-feedback__block">
                        <h3>Điểm mạnh</h3>
                        <p>{feedback.strengths ?? "Chưa có dữ liệu."}</p>
                      </article>
                      <article className="code-review-feedback__block">
                        <h3>Điểm yếu</h3>
                        <p>{feedback.weaknesses ?? "Chưa có dữ liệu."}</p>
                      </article>
                      <article className="code-review-feedback__block code-review-feedback__block--wide">
                        <h3>Gợi ý cải thiện</h3>
                        <p>{feedback.improvement_suggestions ?? "Chưa có dữ liệu."}</p>
                      </article>
                      <article className="code-review-feedback__block code-review-feedback__block--wide">
                        <h3>Phân tích luồng code</h3>
                        <p>{feedback.flow_analysis ?? "Chưa có dữ liệu."}</p>
                      </article>
                    </div>
                  ) : (
                    <div className="lession-detail__empty">
                      <Clock3 size={18} />
                      <span>Nhận xét chưa sẵn sàng. Tải lại sau nếu bài đang được chấm.</span>
                    </div>
                  )}
                </div>
              )}
            </section>

            <aside className="lession-section">
              <div className="lession-section__head">
                <h3>Lịch sử nộp bài</h3>
                <GitPullRequestArrow size={18} />
              </div>

              <div className="lession-detail__meta">
                <div className="lession-detail__meta-item">
                  <span>Điểm hiện tại</span>
                  <strong>{formatScore(totalScore)}</strong>
                </div>
                <div className="lession-detail__meta-item">
                  <span>Trạng thái</span>
                  <strong>{getDisplayStatus(selectedSubmission, Boolean(feedback))}</strong>
                </div>
              </div>

              <div className="code-review-history">
                {submissions.map((submission) => (
                  <button
                    key={submission.id}
                    type="button"
                    className={`code-review-history__item ${
                      selectedDetail?.submission.id === submission.id
                        ? "code-review-history__item--active"
                        : ""
                    }`}
                    onClick={() => void loadDetail(submission.id, submission)}
                  >
                    <span>
                      {getDisplayStatus(
                        submission,
                        selectedDetail?.submission.id === submission.id && Boolean(feedback),
                      )}
                    </span>
                    <strong>
                      {formatScore(
                        selectedDetail?.submission.id === submission.id
                          ? totalScore
                          : submission.score,
                      )}
                    </strong>
                    <small>{formatDate(submission.submitted_at)}</small>
                  </button>
                ))}
              </div>
            </aside>
          </section>
        </section>
      </main>

      <GithubModal
        open={open}
        onClose={() => setOpen(false)}
        assignmentId={assignment?.id ?? ""}
        onUploadSuccess={() => {
          setOpen(false);
          setNotice("Đã nộp liên kết GitHub. Kết quả sẽ hiển thị sau khi hệ thống chấm xong.");
          void loadCodeReview();
        }}
      />
    </>
  );
}
