"""
Central logging configuration for ETF Screener.

Call setup_logging() once at application startup (app_fast.py module level).
Every subsequent call is a no-op that returns the existing logger.

Log files are written to  logs/debug_YYYY-MM-DD_HH-MM-SS.log.
Both file (DEBUG+) and console (INFO+) handlers are attached to the root logger
so that uvicorn, fastapi, and all ETF_screener loggers are captured.

stdout and stderr are wrapped so that terminal output also lands in the log file.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

_log_file: Optional[Path] = None


# ---------------------------------------------------------------------------
# stdout proxy
# ---------------------------------------------------------------------------


class _PrintCapture:
    """
    Thin stream wrapper. Each newline-terminated chunk is forwarded to
    *target_logger* at *level* AND written to the real stream so the
    terminal still shows output.
    """

    def __init__(
        self, target_logger: logging.Logger, real_stdout, level: int = logging.INFO
    ):
        self._logger = target_logger
        self._real = real_stdout
        self._level = level
        self._buf = ""

    def write(self, text: str):
        self._real.write(text)
        self._buf += text
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            stripped = line.rstrip()
            if stripped:
                self._logger.log(self._level, stripped)

    def flush(self):
        if self._buf.strip():
            self._logger.log(self._level, self._buf.rstrip())
            self._buf = ""
        self._real.flush()

    def isatty(self):
        return False

    def __getattr__(self, name):
        return getattr(self._real, name)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def setup_logging(app_name: str = "ETF_screener") -> logging.Logger:
    """
    Configure application-wide logging. Returns the named app logger.
    Idempotent: safe to call on every module import / uvicorn reload.
    """
    global _log_file

    root = logging.getLogger()

    # Guard: don't install a second FileHandler if we already set one up.
    if any(isinstance(h, logging.FileHandler) for h in root.handlers):
        return logging.getLogger(app_name)

    # ---- Create log file ------------------------------------------------
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    _log_file = log_dir / f"debug_{timestamp}.log"

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)-8s] %(name)-28s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler — DEBUG and above (verbose, for post-mortem investigation)
    fh = logging.FileHandler(_log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)

    # Console handler — INFO and above (keeps terminal readable)
    ch = logging.StreamHandler(sys.__stdout__)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)

    root.handlers.clear()
    root.setLevel(logging.DEBUG)
    root.addHandler(fh)
    root.addHandler(ch)

    # ---- Route uvicorn / fastapi loggers through root -------------------
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        lg = logging.getLogger(name)
        lg.handlers.clear()
        lg.propagate = True

    # ---- Capture bare print()/stderr writes -----------------------------
    if not isinstance(sys.stdout, _PrintCapture):
        print_logger = logging.getLogger("print")
        sys.stdout = _PrintCapture(print_logger, sys.__stdout__, level=logging.INFO)

    if not isinstance(sys.stderr, _PrintCapture):
        stderr_logger = logging.getLogger("stderr")
        sys.stderr = _PrintCapture(stderr_logger, sys.__stderr__, level=logging.ERROR)

    # ---- Capture uncaught exceptions ------------------------------------
    def _log_uncaught_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            # Preserve expected Ctrl+C behavior without noisy stack logging.
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logging.getLogger("uncaught").error(
            "Uncaught exception",
            exc_info=(exc_type, exc_value, exc_traceback),
        )

    sys.excepthook = _log_uncaught_exception

    # Python 3.8+: thread exceptions bypass sys.excepthook by default.
    if hasattr(sys, "__stderr__"):
        try:
            import threading

            def _thread_excepthook(args):
                _log_uncaught_exception(
                    args.exc_type, args.exc_value, args.exc_traceback
                )

            threading.excepthook = _thread_excepthook
        except Exception:
            pass

    logger = logging.getLogger(app_name)
    logger.info("Logging initialised -> %s", _log_file)

    # ---- Apply log retention policy (keep only 3 most recent of each type) ----
    cleanup_old_logs(log_dir, "debug_", max_keep=1)
    cleanup_old_logs(log_dir, "console_", max_keep=1)
    cleanup_old_logs(log_dir, "hotlist_", max_keep=1)
    cleanup_old_logs(log_dir, "auto-refresh", max_keep=1)

    return logger


def get_log_file() -> Optional[Path]:
    """Return the path of the active log file (None before setup_logging is called)."""
    return _log_file


def cleanup_old_logs(logs_dir: Path, prefix: str, max_keep: int = 3):
    """Keep only the max_keep most recent log files with the given prefix."""
    import os

    try:
        log_files = sorted(
            [f for f in logs_dir.glob(f"{prefix}*.log")],
            key=lambda x: os.path.getctime(x),
            reverse=True,
        )

        # Remove all but the most recent max_keep files
        for old_file in log_files[max_keep:]:
            try:
                old_file.unlink()
                print(
                    f"[LOG CLEANUP] Deleted old log file: {old_file.name}",
                    file=sys.__stdout__,
                )
            except Exception as e:
                print(
                    f"[LOG CLEANUP] Could not delete {old_file.name}: {str(e)}",
                    file=sys.__stdout__,
                )
    except Exception as e:
        print(
            f"[LOG CLEANUP] Error during cleanup for {prefix}: {str(e)}",
            file=sys.__stdout__,
        )
