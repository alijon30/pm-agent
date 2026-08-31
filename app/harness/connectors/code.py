"""Read-only search over a checked-out repository."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

MAX_FILE_BYTES = 512_000


class CodeSearch:
    def __init__(self, repo_root: Path | str) -> None:
        self._root = Path(repo_root).resolve()

    def _resolve(self, path: str) -> Path | None:
        """Absolute path inside the repo, or None if it escapes or does not exist."""
        candidate = (self._root / path).resolve()
        if not candidate.is_relative_to(self._root) or not candidate.is_file():
            return None
        return candidate

    def grep(
        self, pattern: str, *, glob: str = "**/*.py", max_hits: int = 20
    ) -> list[dict[str, Any]]:
        """Case-insensitive regex over matching files. Returns {path, line, text} per hit, with
        paths relative to the repo root so they can be cited directly."""
        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error:
            return []
        hits: list[dict[str, Any]] = []
        for file in sorted(self._root.glob(glob)):
            if not file.is_file() or file.stat().st_size > MAX_FILE_BYTES:
                continue
            if any(part in {".git", "__pycache__", ".venv"} for part in file.parts):
                continue
            try:
                lines = file.read_text(errors="replace").splitlines()
            except OSError:
                continue
            for number, line in enumerate(lines, start=1):
                if regex.search(line):
                    hits.append({
                        "path": str(file.relative_to(self._root)),
                        "line": number,
                        "text": line.strip()[:300],
                    })
                    if len(hits) >= max_hits:
                        return hits
        return hits

    def read(self, path: str, start: int, end: int) -> str:
        """1-indexed inclusive line window. Empty string when the path is outside the repo."""
        file = self._resolve(path)
        if file is None:
            return ""
        lines = file.read_text(errors="replace").splitlines()
        first = max(1, start)
        return "\n".join(lines[first - 1 : max(first, end)])

    def exists(self, path: str, line: int | None = None) -> bool:
        """Does this citation point at something real? A line beyond the file is not real."""
        file = self._resolve(path)
        if file is None:
            return False
        if line is None:
            return True
        return 1 <= line <= len(file.read_text(errors="replace").splitlines())
