import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import axios from "axios";
import { Github, Loader2, X } from "lucide-react";
import { api } from "@/api/axios";
import "./lession.css";

type GithubModalProps = {
    open: boolean;
    assignmentId: string;
    onClose: () => void;
    onUploadSuccess: () => void;
};

export default function GithubModal({
    open,
    assignmentId,
    onClose,
    onUploadSuccess,
}: GithubModalProps) {
    const [githubRepoUrl, setGithubRepoUrl] = useState("");
    const [commitHash, setCommitHash] = useState("");
    const [error, setError] = useState<string | null>(null);
    const [submitting, setSubmitting] = useState(false);

    useEffect(() => {
        if (!open) {
            return;
        }
        const previousOverflow = document.body.style.overflow;
        document.body.style.overflow = "hidden";

        const handleKeydown = (event: KeyboardEvent) => {
            if (event.key === "Escape" && !submitting) {
                onClose();
            }
        };
        window.addEventListener("keydown", handleKeydown);

        return () => {
            document.body.style.overflow = previousOverflow;
            window.removeEventListener("keydown", handleKeydown);
        };
    }, [open, onClose, submitting]);

    useEffect(() => {
        if (!open) {
            return;
        }
        setError(null);
        setCommitHash("");
    }, [open]);

    if (!open || typeof document === "undefined") {
        return null;
    }

    const handleUpload = async () => {
        const trimmedGithub = githubRepoUrl.trim();
        const trimmedCommit = commitHash.trim();
        setError(null);
        if (!assignmentId) {
            setError("Không tìm thấy bài tập để nộp mã nguồn.");
            return;
        }
        if (!trimmedGithub) {
            setError("Vui lòng nhập liên kết kho GitHub.");
            return;
        }
        if (!/^https:\/\/(www\.)?github\.com\/[^/]+\/[^/]+\/?/.test(trimmedGithub)) {
            setError("Liên kết GitHub không hợp lệ.");
            return;
        }
        try {
            setSubmitting(true);
            await api.post("/code-submissions", {
                assignment_id: assignmentId,
                github_repo_url: trimmedGithub,
                commit_hash: trimmedCommit || null,
            });
            
            setGithubRepoUrl("");
            setCommitHash("");
            onUploadSuccess();
        } catch (error) {
            if (axios.isAxiosError(error)) {
                const detail = error.response?.data?.detail;
                setError(typeof detail === "string" ? detail : "Không thể nộp liên kết GitHub.");
                return;
            }
            setError("Không thể nộp liên kết GitHub.");
        } finally {
            setSubmitting(false);
        }
    };

    return createPortal(
        <div className="github-modal" role="dialog" aria-modal="true">
            <div className="github-modal__content">
                <div className="github-modal__header">
                    <div>
                        <span className="github-modal__eyebrow">Nộp bài GitHub</span>
                        <h2>Nộp liên kết kho mã nguồn</h2>
                    </div>
                    <button
                        type="button"
                        className="github-modal__close"
                        onClick={onClose}
                        disabled={submitting}
                        aria-label="Đóng"
                    >
                        <X size={18} />
                    </button>
                </div>

                <div className="github-modal__body">
                    <label className="github-modal__field" htmlFor="github-repo-url">
                        <span>Liên kết kho mã nguồn</span>
                        <input
                            type="url"
                            id="github-repo-url"
                            placeholder="https://github.com/owner/repository"
                            value={githubRepoUrl}
                            onChange={(e) => setGithubRepoUrl(e.target.value)}
                            disabled={submitting}
                        />
                    </label>

                    <label className="github-modal__field" htmlFor="github-commit">
                        <span>Commit/ref tùy chọn</span>
                        <input
                            type="text"
                            id="github-commit"
                            placeholder="main, develop hoặc mã commit"
                            value={commitHash}
                            onChange={(e) => setCommitHash(e.target.value)}
                            disabled={submitting}
                        />
                    </label>

                    {error ? <p className="github-modal__error">{error}</p> : null}
                </div>

                <div className="github-modal__footer">
                    <button
                        type="button"
                        className="github-modal__submit"
                        onClick={() => void handleUpload()}
                        disabled={submitting}
                    >
                        {submitting ? <Loader2 size={18} className="github-modal__spinner" /> : <Github size={18} />}
                        {submitting ? "Đang nộp và chấm..." : "Nộp bài"}
                    </button>
                </div>
            </div>
        </div>,
        document.body,
    );
}
