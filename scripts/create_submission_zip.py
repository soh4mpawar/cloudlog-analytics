"""Packages the CloudLog Analytics project into a clean distribution ZIP.

Includes:
- Application source (`app.py`, `cloudlog/`)
- Configuration (`requirements.txt`, `.streamlit/config.toml`, `.gitignore`)
- Data & Generator (`data/sample_logs.csv`, `data/generate_sample.py`)
- Test suite & fixtures (`tests/`)
- Documentation & Reports (`docs/REPORT.docx`, `docs/REPORT.pdf`, `docs/REPORT_DRAFT.md`, `docs/DEMO_SCRIPT.md`, `docs/VIVA_PREP.md`)
- README (`README.md`)
- Verified UI screenshots (`screenshots/`)

Strictly Excludes:
- Virtual environments (`.venv/`)
- Git directories (`.git/`)
- Bytecode & caches (`__pycache__/`, `.pytest_cache/`, `*.pyc`)
- Local logs (`*.log`)
- The output zip itself and `dist/` directory
"""

import os
import zipfile

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DIST_DIR = os.path.join(PROJECT_ROOT, "dist")
ZIP_NAME = "CloudLog_Analytics_Submission.zip"
ZIP_PATH = os.path.join(DIST_DIR, ZIP_NAME)

EXCLUDED_DIRS = {
    ".venv",
    "venv",
    ".git",
    "__pycache__",
    ".pytest_cache",
    "dist",
    ".idea",
    ".vscode",
}

EXCLUDED_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".log",
    ".tmp",
    ".zip",
}

EXCLUDED_FILES = {
    "bad_data.csv",
    ".DS_Store",
    "Thumbs.db",
}


def build_submission_zip():
    os.makedirs(DIST_DIR, exist_ok=True)
    if os.path.exists(ZIP_PATH):
        os.remove(ZIP_PATH)

    included_files = []

    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(PROJECT_ROOT):
            # Prune excluded directories in-place
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS and not d.endswith(".venv")]

            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in EXCLUDED_EXTENSIONS or file in EXCLUDED_FILES:
                    continue

                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, PROJECT_ROOT)

                # Avoid adding anything from dist
                if rel_path.startswith("dist"):
                    continue

                zf.write(full_path, arcname=rel_path)
                included_files.append((rel_path, os.path.getsize(full_path)))

    print(f"Created submission ZIP at: {ZIP_PATH}")
    print(f"Total packaged files: {len(included_files)}")
    total_size = sum(sz for _, sz in included_files)
    print(f"Uncompressed archive payload: {total_size / (1024 * 1024):.2f} MB")
    print(f"Compressed ZIP size: {os.path.getsize(ZIP_PATH) / (1024 * 1024):.2f} MB\n")

    print("--- Packaged Contents ---")
    for path, sz in sorted(included_files):
        print(f"  {path:<60} ({sz:,} bytes)")


if __name__ == "__main__":
    build_submission_zip()
