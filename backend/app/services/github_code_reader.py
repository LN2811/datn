import os
import re
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import requests
from fastapi import HTTPException


ALLOWED_EXTENSIONS = {
    ".py",
    ".js",
    ".java",
    ".cpp",
    ".c",
    ".cs",
    ".go",
    ".rb",
    ".php",
    ".ts",
    ".tsx",
    ".jsx",
    ".html",
    ".css",
    ".json",
    ".xml",
    ".yaml",
    ".yml",
    ".sh",
    ".bat",
    ".ps1",
}

IGNORE_DIRS = {
    ".git",
    ".github",
    "node_modules",
    "vendor",
    "__pycache__",
    "dist",
    "build",
    "target",
    ".next",
    ".venv",
    "venv",
    ".idea",
    ".vscode",
}

MAX_FILES = 40
MAX_FILE_BYTES = 200_000
MAX_TOTAL_CHARS = 60_000
MAX_ZIP_BYTES = 25_000_000
MAX_EXTRACTED_BYTES = 50_000_000


@dataclass
class GithubFileContent:
    path: str
    content: str


@dataclass
class GithubCodeSnapshot:
    repo_url: str
    owner: str
    repo_name: str
    branch: str
    commit_hash: str | None
    files: list[GithubFileContent]
    combined_content: str


class GithubCodeReader:
    @staticmethod
    def read_code_repo(github_repo_url: str, ref: str | None = None) -> GithubCodeSnapshot:
        owner, repo_name = GithubCodeReader._parse_github_url(github_repo_url)

        repo_meta = GithubCodeReader._get_repo_metadata(
            owner=owner,
            repo_name=repo_name,
        )
        default_branch = repo_meta.get("default_branch") or "main"
        requested_ref = (ref or "").strip() or default_branch

        commit_hash = GithubCodeReader._get_latest_commit_hash(
            owner=owner,
            repo=repo_name,
            branch=requested_ref,
        )

        zip_bytes = GithubCodeReader._download_repo_zip(
            owner=owner,
            repo=repo_name,
            branch=requested_ref,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "repo.zip"
            extracted_path = Path(tmpdir) / "extracted"

            zip_path.write_bytes(zip_bytes)
            extracted_path.mkdir(parents=True, exist_ok=True)

            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                GithubCodeReader._safe_extract(zip_ref, extracted_path)

            repo_root = GithubCodeReader._find_extracted_root(extracted_path)
            files = GithubCodeReader._collect_code_files(repo_root)

        if not files:
            raise HTTPException(
                status_code=400,
                detail="No code files found in the repository.",
            )

        combined_content = GithubCodeReader._combine_files(files)

        return GithubCodeSnapshot(
            repo_url=github_repo_url,
            owner=owner,
            repo_name=repo_name,
            branch=requested_ref,
            commit_hash=commit_hash,
            files=files,
            combined_content=combined_content,
        )

    @staticmethod
    def _parse_github_url(github_repo_url: str) -> tuple[str, str]:
        parsed = urlparse((github_repo_url or "").strip())

        if parsed.netloc.lower() not in {"github.com", "www.github.com"}:
            raise HTTPException(
                status_code=400,
                detail="Invalid GitHub repository URL.",
            )

        parts = [part for part in parsed.path.strip("/").split("/") if part]

        if len(parts) < 2:
            raise HTTPException(
                status_code=400,
                detail="GitHub repository URL must include owner and repo name.",
            )

        owner = parts[0]
        repo_name = parts[1].removesuffix(".git")

        if not re.match(r"^[A-Za-z0-9_.-]+$", owner):
            raise HTTPException(
                status_code=400,
                detail="Invalid GitHub owner.",
            )

        if not re.match(r"^[A-Za-z0-9_.-]+$", repo_name):
            raise HTTPException(
                status_code=400,
                detail="Invalid GitHub repository name.",
            )

        return owner, repo_name

    @staticmethod
    def _github_headers() -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "CodeMasterApp/1.0",
        }

        github_token = os.getenv("GITHUB_TOKEN")
        if github_token:
            headers["Authorization"] = f"token {github_token}"

        return headers

    @staticmethod
    def _get_repo_metadata(
        *,
        owner: str,
        repo_name: str,
    ) -> dict:
        url = f"https://api.github.com/repos/{owner}/{repo_name}"

        response = requests.get(
            url,
            headers=GithubCodeReader._github_headers(),
            timeout=20,
        )

        if response.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail="GitHub repository not found or private.",
            )

        if response.status_code >= 400:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"GitHub API error: {response.text}",
            )

        return response.json()

    @staticmethod
    def _get_latest_commit_hash(
        *,
        owner: str,
        repo: str,
        branch: str,
    ) -> str | None:
        url = f"https://api.github.com/repos/{owner}/{repo}/commits/{branch}"

        response = requests.get(
            url,
            headers=GithubCodeReader._github_headers(),
            timeout=20,
        )

        if response.status_code >= 400:
            return None

        data = response.json()
        return data.get("sha")

    @staticmethod
    def _download_repo_zip(
        *,
        owner: str,
        repo: str,
        branch: str,
    ) -> bytes:
        url = f"https://api.github.com/repos/{owner}/{repo}/zipball/{branch}"

        response = requests.get(
            url,
            headers=GithubCodeReader._github_headers(),
            timeout=60,
        )

        if response.status_code >= 400:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"GitHub API error: {response.text}",
            )

        content_length = response.headers.get("content-length")
        if content_length and int(content_length) > MAX_ZIP_BYTES:
            raise HTTPException(
                status_code=413,
                detail="GitHub repository archive is too large.",
            )

        if len(response.content) > MAX_ZIP_BYTES:
            raise HTTPException(
                status_code=413,
                detail="GitHub repository archive is too large.",
            )

        return response.content

    @staticmethod
    def _safe_extract(
        zip_file: zipfile.ZipFile,
        extract_to: Path,
    ) -> None:
        target_dir = extract_to.resolve()
        extracted_size = 0

        for member in zip_file.infolist():
            extracted_size += member.file_size
            if extracted_size > MAX_EXTRACTED_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail="GitHub repository archive is too large after extraction.",
                )

            destination = (target_dir / member.filename).resolve()

            try:
                destination.relative_to(target_dir)
            except ValueError as exc:
                raise HTTPException(
                    status_code=400,
                    detail="Unsafe file path in ZIP archive.",
                ) from exc

            zip_file.extract(member, target_dir)

    @staticmethod
    def _find_extracted_root(extracted_dir: Path) -> Path:
        children = [
            child
            for child in extracted_dir.iterdir()
            if child.is_dir()
        ]

        if children:
            return children[0]

        return extracted_dir

    @staticmethod
    def _should_ignore(path: Path) -> bool:
        return any(part in IGNORE_DIRS for part in path.parts)

    @staticmethod
    def _collect_code_files(repo_root: Path) -> list[GithubFileContent]:
        collected_files: list[GithubFileContent] = []
        total_chars = 0

        all_files = sorted(
            [path for path in repo_root.rglob("*") if path.is_file()],
            key=lambda item: str(item).lower(),
        )

        for file_path in all_files:
            if len(collected_files) >= MAX_FILES:
                break

            relative_path = file_path.relative_to(repo_root)

            if GithubCodeReader._should_ignore(relative_path):
                continue

            if file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
                continue

            try:
                if file_path.stat().st_size > MAX_FILE_BYTES:
                    continue

                content = file_path.read_text(
                    encoding="utf-8",
                    errors="ignore",
                ).strip()
            except Exception:
                continue

            if not content:
                continue

            remaining_chars = MAX_TOTAL_CHARS - total_chars

            if remaining_chars <= 0:
                break

            if len(content) > remaining_chars:
                content = content[:remaining_chars]

            collected_files.append(
                GithubFileContent(
                    path=str(relative_path).replace("\\", "/"),
                    content=content,
                )
            )

            total_chars += len(content)

        return collected_files

    @staticmethod
    def _combine_files(files: list[GithubFileContent]) -> str:
        parts: list[str] = []

        for file in files:
            parts.append(
                f"// File: {file.path}\n{file.content}\n"
            )

        return "\n".join(parts).strip()
