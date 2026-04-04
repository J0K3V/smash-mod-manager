"""
file_source.py — Abstraction layer for file sources.

Supports local filesystem now. Designed so remote sources
(Synology NAS, network share, etc.) can be added later
without rewriting the rest of the codebase.
"""
import os
import shutil
import zipfile
import re
from abc import ABC, abstractmethod

from core import logger


class FileSource(ABC):
    """Abstract base class for file sources."""

    @abstractmethod
    def exists(self, path: str) -> bool:
        """Check if a file or folder exists."""
        ...

    @abstractmethod
    def is_dir(self, path: str) -> bool:
        ...

    @abstractmethod
    def list_dir(self, path: str) -> list[str]:
        ...

    @abstractmethod
    def list_files_recursive(self, path: str) -> set[str]:
        """List all files recursively, returning relative paths."""
        ...

    @abstractmethod
    def copy_file(self, src: str, dst_local: str) -> bool:
        """Copy a file from the source to a local destination."""
        ...

    @abstractmethod
    def get_name(self) -> str:
        ...


class LocalFileSource(FileSource):
    """Local filesystem source."""

    def __init__(self, root: str):
        self.root = root

    def exists(self, path: str) -> bool:
        return os.path.exists(os.path.join(self.root, path))

    def is_dir(self, path: str) -> bool:
        return os.path.isdir(os.path.join(self.root, path))

    def list_dir(self, path: str) -> list[str]:
        full = os.path.join(self.root, path)
        if os.path.isdir(full):
            return os.listdir(full)
        return []

    def list_files_recursive(self, path: str) -> set[str]:
        full = os.path.join(self.root, path)
        result = set()
        if not os.path.isdir(full):
            return result
        for dirpath, dirnames, filenames in os.walk(full):
            for f in filenames:
                rel = os.path.relpath(os.path.join(dirpath, f), full)
                result.add(rel.replace(os.sep, "/"))
        return result

    def copy_file(self, src: str, dst_local: str) -> bool:
        full_src = os.path.join(self.root, src)
        if not os.path.isfile(full_src):
            return False
        os.makedirs(os.path.dirname(dst_local), exist_ok=True)
        shutil.copy2(full_src, dst_local)
        return True

    def get_name(self) -> str:
        return f"Local: {self.root}"


class ZipFileSource(FileSource):
    """
    Read-only file source backed by a .zip archive.
    Detects an optional root prefix inside the zip (e.g. 'MarioMod/fighter/…')
    and strips it so all paths are relative to the mod root.
    """

    def __init__(self, zip_path: str):
        self.zip_path = zip_path
        self._zf = zipfile.ZipFile(zip_path, "r")
        self._prefix = self._detect_prefix()

    # ── internal helpers ───────────────────────────────────────────────────

    def _detect_prefix(self) -> str:
        """
        If all entries share a common top-level folder that is NOT a standard
        Smash mod root folder (fighter/ui/effect/sound/…), treat it as a
        wrapper prefix and strip it.
        """
        SMASH_ROOTS = {"fighter", "ui", "effect", "sound", "camera", "stream", "stage"}
        names = [n for n in self._zf.namelist() if not n.endswith("/")]
        if not names:
            return ""
        tops = {n.split("/")[0] for n in names}
        if len(tops) == 1:
            top = tops.pop()
            if top not in SMASH_ROOTS:
                return top + "/"
        return ""

    def _full(self, path: str) -> str:
        """Build the internal zip path (with prefix) from a relative path."""
        if not path:
            return self._prefix.rstrip("/")
        return self._prefix + path.lstrip("/")

    def _members(self) -> list[str]:
        """All zip entries stripped of the prefix."""
        return [
            n[len(self._prefix):]
            for n in self._zf.namelist()
            if n.startswith(self._prefix)
        ]

    # ── FileSource interface ───────────────────────────────────────────────

    def exists(self, path: str) -> bool:
        full = self._full(path)
        for n in self._zf.namelist():
            if n == full or n == full + "/" or n.startswith(full + "/"):
                return True
        return False

    def is_dir(self, path: str) -> bool:
        full = self._full(path)
        for n in self._zf.namelist():
            if n.startswith(full + "/"):
                return True
        return False

    def list_dir(self, path: str) -> list[str]:
        full = self._full(path)
        prefix = full + "/" if full else ""
        seen = set()
        for n in self._zf.namelist():
            if not n.startswith(prefix):
                continue
            rest = n[len(prefix):]
            if not rest:
                continue
            name = rest.split("/")[0]
            seen.add(name)
        return sorted(seen)

    def list_files_recursive(self, path: str) -> set[str]:
        full = self._full(path)
        prefix = full + "/" if full else ""
        result = set()
        for n in self._zf.namelist():
            if n.endswith("/"):
                continue
            if n.startswith(prefix):
                result.add(n[len(prefix):].replace("/", "/"))
        return result

    def copy_file(self, src: str, dst_local: str) -> bool:
        full = self._full(src)
        try:
            data = self._zf.read(full)
        except KeyError:
            return False
        os.makedirs(os.path.dirname(dst_local), exist_ok=True)
        with open(dst_local, "wb") as f:
            f.write(data)
        return True

    def get_name(self) -> str:
        return f"Zip: {os.path.basename(self.zip_path)}"

    def close(self):
        self._zf.close()

    # ── Smash-specific helpers ─────────────────────────────────────────────

    def detect_fighter(self) -> str | None:
        """Detect fighter name from fighter/<name>/ inside the zip."""
        SMASH_ROOTS = {"fighter", "ui", "effect", "sound", "camera"}
        for entry in self.list_dir("fighter"):
            if entry not in ("kirby",):
                return entry
        for entry in self.list_dir("fighter"):
            return entry
        for entry in self.list_dir("effect/fighter"):
            return entry
        return None

    def detect_model_parts(self, fighter: str) -> list[str]:
        """Return model part names (body, cape, pipe, etc.) that exist in the zip."""
        return [
            e for e in self.list_dir(f"fighter/{fighter}/model")
            if self.is_dir(f"fighter/{fighter}/model/{e}")
        ]

    def detect_slots(self, fighter: str) -> list[str]:
        """Return sorted slot names (c00, c01, …) found across all model parts."""
        slots: set[str] = set()
        for part in self.detect_model_parts(fighter):
            base = f"fighter/{fighter}/model/{part}"
            for entry in self.list_dir(base):
                if re.match(r'^c\d{2,3}$', entry):
                    slots.add(entry)
        return sorted(slots)

    def extract_to(self, fighter: str, slot: str, out_root: str) -> int:
        """
        Copy only the folders that exist for `slot` in the zip to out_root.
        Returns count of files written.
        """
        parts = self.detect_model_parts(fighter)
        count = 0
        for part in parts:
            src_prefix = f"fighter/{fighter}/model/{part}/{slot}/"
            if not self.is_dir(f"fighter/{fighter}/model/{part}/{slot}"):
                continue
            for rel_file in self.list_files_recursive(
                    f"fighter/{fighter}/model/{part}/{slot}"):
                src = src_prefix + rel_file
                dst = os.path.join(
                    out_root, "fighter", fighter, "model", part, slot, rel_file)
                if self.copy_file(src, dst):
                    count += 1
        return count


class RemoteFileSource(FileSource):
    """
    Placeholder for remote file source (Synology NAS, network share, etc.).
    Implement when the remote server feature is ready.
    """

    def __init__(self, host: str, port: int = 0, path: str = ""):
        self.host = host
        self.port = port
        self.path = path
        logger.warn("RemoteFileSource is a placeholder — not yet implemented.")

    def exists(self, path: str) -> bool:
        raise NotImplementedError("Remote source not yet implemented")

    def is_dir(self, path: str) -> bool:
        raise NotImplementedError

    def list_dir(self, path: str) -> list[str]:
        raise NotImplementedError

    def list_files_recursive(self, path: str) -> set[str]:
        raise NotImplementedError

    def copy_file(self, src: str, dst_local: str) -> bool:
        raise NotImplementedError

    def get_name(self) -> str:
        return f"Remote: {self.host}:{self.port}/{self.path} (not implemented)"
