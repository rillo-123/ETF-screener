"""Age, file-count and byte limits for regenerable caches only."""

import logging
import os
import threading
import time
from pathlib import Path

from ETF_screener.config_loader import get_paths

logger = logging.getLogger(__name__)
_lock = threading.Lock()


def cache_is_fresh(path: Path) -> bool:
    """Expired or concurrently evicted cache files are ordinary cache misses."""
    max_age = float(get_paths().get("cache_policy", {}).get("max_age_days", 14)) * 86400
    try:
        return path.is_file() and time.time() - path.stat().st_mtime <= max_age
    except FileNotFoundError:
        return False


def trim_cache() -> dict[str, int]:
    """Evict oldest derived files after a write, preserving price/history files.

    Only the configured cache root is managed. Never recurse through links or
    delete directories. Concurrent processes may evict each other's cache files;
    callers already treat a missing cache as a normal cache miss.
    """
    paths = get_paths()
    root = Path(paths["data"]["cache"]).resolve()
    limits = paths.get("cache_policy", {})
    max_bytes = int(limits.get("max_bytes", 1_073_741_824))
    max_files = int(limits.get("max_files", 5000))
    max_age = float(limits.get("max_age_days", 14)) * 86400
    if min(max_bytes, max_files, max_age) < 0:
        raise ValueError("Cache limits cannot be negative")
    removed = freed = 0
    with _lock:
        entries = []
        # os.walk avoids following directory junctions/symlinks.
        for directory, dirs, files in os.walk(root, followlinks=False):
            dirs[:] = [
                d
                for d in dirs
                if not (Path(directory) / d).is_symlink()
                and (Path(directory) / d).resolve().is_relative_to(root)
            ]
            for name in files:
                path = Path(directory) / name
                if path.suffix not in {".parquet", ".pkl"} or name.endswith(
                    "_data.parquet"
                ):
                    continue
                if path.is_symlink() or not path.resolve().is_relative_to(root):
                    continue
                try:
                    stat = path.stat()
                    entries.append((stat.st_mtime, stat.st_size, path))
                except FileNotFoundError:
                    pass
        total = sum(size for _, size, _ in entries)
        count = len(entries)
        cutoff = time.time() - max_age
        for mtime, size, path in sorted(entries):
            if mtime >= cutoff and total <= max_bytes and count <= max_files:
                break
            try:
                path.unlink()
                removed += 1
                freed += size
            except FileNotFoundError:
                pass
            except OSError as exc:
                logger.warning("Could not evict cache %s: %s", path, exc)
                continue
            total -= size
            count -= 1
    return {"removed": removed, "freed_bytes": freed, "remaining_bytes": total}
