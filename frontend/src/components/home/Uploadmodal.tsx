import { useCallback, useEffect, useState } from "react";
import { createPortal } from "react-dom";

import { api } from "@/api/axios";

import "./project.css";

type UploadModalProps = {
  open: boolean;
  projectId: string;
  onClose: () => void;
  onUploadSuccess: () => void;
};

export default function UploadModal({
  open,
  projectId,
  onClose,
  onUploadSuccess,
}: UploadModalProps) {
  const [title, setTitle] = useState("");
  const [externalLink, setExternalLink] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [fileInputKey, setFileInputKey] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

  const resetForm = () => {
    setTitle("");
    setExternalLink("");
    setFile(null);
    setFileInputKey((currentKey) => currentKey + 1);
    setError(null);
  };

  const closeModal = useCallback(() => {
    resetForm();
    onClose();
  }, [onClose]);

  useEffect(() => {
    if (!open) {
      return;
    }

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !uploading) {
        closeModal();
      }
    };

    window.addEventListener("keydown", handleKeyDown);

    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [open, closeModal, uploading]);

  useEffect(() => {
    if (!open) {
      return;
    }

    setError(null);
  }, [open]);

  if (!open || typeof document === "undefined") {
    return null;
  }

  const handleUpload = async () => {
    const trimmedTitle = title.trim();
    const trimmedExternalLink = externalLink.trim();

    setError(null);

    if (!trimmedTitle) {
      setError("Vui lòng nhập tiêu đề tài liệu.");
      return;
    }

    if (!file && !trimmedExternalLink) {
      setError("Vui lòng chọn tệp hoặc nhập liên kết bên ngoài.");
      return;
    }

    if (file && trimmedExternalLink) {
      setError("Chỉ chọn một trong hai: tệp hoặc liên kết bên ngoài.");
      return;
    }

    try {
      setUploading(true);

      const formData = new FormData();
      formData.append("title", trimmedTitle);

      if (file) {
        formData.append("file_path", file);
      }

      if (trimmedExternalLink) {
        formData.append("external_link", trimmedExternalLink);
      }

      await api.post(
        `/learning-materials/project/${projectId}/materials`,
        formData,
        {
          headers: {
            "Content-Type": "multipart/form-data",
          },
        },
      );

      setTitle("");
      setExternalLink("");
      setFile(null);
      setFileInputKey((currentKey) => currentKey + 1);
      onUploadSuccess();
      closeModal();
    } catch {
      setError("Không thể tải tài liệu lên.");
    } finally {
      setUploading(false);
    }
  };

  return createPortal(
    <div
      className="upload-modal"
      onClick={() => {
        if (!uploading) {
          closeModal();
        }
      }}
      role="presentation"
    >
      <div
        className="upload-modal__content"
        onClick={(event) => event.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="upload-modal-title"
      >
        <div className="upload-modal__header">
          <h2 id="upload-modal-title">Tải tài liệu học tập</h2>
          <button
            type="button"
            className="upload-modal__close"
            onClick={closeModal}
            disabled={uploading}
            aria-label="Đóng cửa sổ tải tài liệu"
          >
            x
          </button>
        </div>

        {error ? <p className="upload-modal__error">{error}</p> : null}

        <label className="upload-modal__field">
          <span>Tiêu đề</span>
          <input
            className="upload-modal__input"
            type="text"
            placeholder="Nhập tiêu đề tài liệu"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
          />
        </label>

        <label className="upload-modal__field">
          <span>Liên kết bên ngoài</span>
          <input
            className="upload-modal__input"
            type="url"
            placeholder="https://..."
            value={externalLink}
            onChange={(event) => setExternalLink(event.target.value)}
          />
        </label>

        <label className="upload-modal__field">
          <span>Tệp</span>
          <input
            className="upload-modal__input"
            type="file"
            key={fileInputKey}
            accept=".pdf,.docx,.pptx,.txt,.jpg,.jpeg,.png"
            onChange={(event) =>
              setFile(event.target.files ? event.target.files[0] : null)
            }
          />
        </label>

        <div className="upload-modal__actions">
          <button
            type="button"
            className="upload-modal__button upload-modal__button--ghost"
            onClick={closeModal}
            disabled={uploading}
          >
            Hủy
          </button>
          <button
            type="button"
            className="upload-modal__button upload-modal__button--primary"
            onClick={handleUpload}
            disabled={uploading}
          >
            {uploading ? "Đang tải lên..." : "Tải lên"}
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
