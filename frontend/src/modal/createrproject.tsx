import { useState } from "react";
import { createPortal } from "react-dom";

import { api } from "@/api/axios";

import "./createrproject.css";

type CreatedProject = {
  id: string;
  name: string;
  description?: string | null;
};

type Props = {
  open: boolean;
  onClose: () => void;
  onSuccess?: (project: CreatedProject) => void | Promise<void>;
};

export default function CreateProjectModal({ open, onClose, onSuccess }: Props) {
  const [projectName, setProjectName] = useState("");
  const [projectDescription, setProjectDescription] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  if (!open) {
    return null;
  }

  const resetForm = () => {
    setProjectName("");
    setProjectDescription("");
    setError("");
  };

  const handleClose = () => {
    if (loading) {
      return;
    }

    resetForm();
    onClose();
  };

  const handleCreate = async () => {
    const name = projectName.trim();
    const description = projectDescription.trim();

    if (!name) {
      setError("Vui long nhap ten project.");
      return;
    }

    if (name.length < 3) {
      setError("Ten project can it nhat 3 ky tu.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const response = await api.post<CreatedProject>("/projects", {
        name,
        description,
      });

      resetForm();
      onClose();
      await onSuccess?.(response.data);
    } catch {
      setError("Tao project that bai.");
    } finally {
      setLoading(false);
    }
  };

  return createPortal(
    <div className="create-project-modal" onClick={handleClose}>
      <div
        className="create-project-modal__content"
        role="dialog"
        aria-modal="true"
        aria-labelledby="create-project-title"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="create-project-modal__header">
          <div>
            <span>Create project</span>
            <h2 id="create-project-title">Tao Project</h2>
          </div>
          <button
            className="create-project-modal__close"
            type="button"
            onClick={handleClose}
            disabled={loading}
            aria-label="Dong modal tao project"
          >
            x
          </button>
        </div>

        {error ? <p className="create-project-modal__error">{error}</p> : null}

        <label className="create-project-modal__field">
          <span>Ten project</span>
          <input
            placeholder="Vi du: AI Readiness"
            value={projectName}
            onChange={(event) => setProjectName(event.target.value)}
            disabled={loading}
          />
        </label>

        <label className="create-project-modal__field">
          <span>Mo ta</span>
          <textarea
            placeholder="Mo ta muc tieu hoac noi dung hoc cua project."
            value={projectDescription}
            onChange={(event) => setProjectDescription(event.target.value)}
            disabled={loading}
            rows={4}
          />
        </label>

        <div className="create-project-modal__actions">
          <button
            className="create-project-modal__button create-project-modal__button--ghost"
            type="button"
            onClick={handleClose}
            disabled={loading}
          >
            Huy
          </button>
          <button
            className="create-project-modal__button create-project-modal__button--primary"
            type="button"
            onClick={() => void handleCreate()}
            disabled={loading}
          >
            {loading ? "Dang tao..." : "Tao project"}
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
