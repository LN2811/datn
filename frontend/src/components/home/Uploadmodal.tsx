import { useEffect, useState } from "react";
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
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    if (!open) {
      return;
    }

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !uploading) {
        onClose();
      }
    };

    window.addEventListener("keydown", handleKeyDown);

    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [open, onClose, uploading]);

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
      setError("Please enter a title.");
      return;
    }

    if (!file && !trimmedExternalLink) {
      setError("Please provide either a file or an external link.");
      return;
    }

    if (file && trimmedExternalLink) {
      setError("Please provide only one of file or external link.");
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
      onUploadSuccess();
      onClose();
    } catch {
      setError("Failed to upload material.");
    } finally {
      setUploading(false);
    }
  };

  return createPortal(
    <div
      className="upload-modal"
      onClick={() => {
        if (!uploading) {
          onClose();
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
          <h2 id="upload-modal-title">Upload Learning Material</h2>
          <button
            type="button"
            className="upload-modal__close"
            onClick={onClose}
            disabled={uploading}
            aria-label="Close upload modal"
          >
            x
          </button>
        </div>

        {error ? <p className="upload-modal__error">{error}</p> : null}

        <label className="upload-modal__field">
          <span>Title</span>
          <input
            className="upload-modal__input"
            type="text"
            placeholder="Enter material title"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
          />
        </label>

        <label className="upload-modal__field">
          <span>External Link</span>
          <input
            className="upload-modal__input"
            type="url"
            placeholder="https://..."
            value={externalLink}
            onChange={(event) => setExternalLink(event.target.value)}
          />
        </label>

        <label className="upload-modal__field">
          <span>File</span>
          <input
            className="upload-modal__input"
            type="file"
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
            onClick={onClose}
            disabled={uploading}
          >
            Cancel
          </button>
          <button
            type="button"
            className="upload-modal__button upload-modal__button--primary"
            onClick={handleUpload}
            disabled={uploading}
          >
            {uploading ? "Uploading..." : "Upload"}
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
