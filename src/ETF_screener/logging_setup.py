"""
Central logging configuration for ETF Screener.

Call setup_logging() once at application startup (app_fast.py module level).
Every subsequent call is a no-op that returns the existing logger.

Log files are written to  logs/debug_YYYY-MM-DD_HH-MM-SS.log.
Both file (DEBUG+) and console (INFO+) handlers are attached to the root logger
so that uvicorn, fastapi, and all ETF_screener loggers are captured.

stdout is wrapped so that legacy print() calls also land in the log file.
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
    Thin sys.stdout wrapper.  Each newline-terminated chunk is forwarded to
    *target_logger* at INFO level AND written to the real stdout so the
    terminal still shows output.
    """

    def __init__(self, target_logger: logging.Logger, real_stdout):
        self._logger = target_logger
        self._real = real_stdout
        self._buf = ""

    def write(self, text: str):
        self._real.write(text)
        self._buf += text
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            stripped = line.rstrip()
            if stripped:
                self._logger.info(stripped)

    def flush(self):
        if self._buf.strip():
            self._logger.info(self._buf.rstrip())
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

    # ---- Capture bare print() calls ------------------------------------
    if not isinstance(sys.stdout, _PrintCapture):
        print_logger = logging.getLogger("print")
        sys.stdout = _PrintCapture(print_logger, sys.__stdout__)

    logger = logging.getLogger(app_name)
    logger.info("Logging initialised -> %s", _log_file)
    return logger


def get_log_file() -> Optional[Path]:
    """Return the path of the active log file (None before setup_logging is called)."""
    return _log_file
