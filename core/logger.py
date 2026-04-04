"""
logger.py — Thread-safe centralized logger.
GUI panels subscribe via callback. File logging with session rotation.
"""
import os
import threading
from datetime import datetime

_lock = threading.Lock()
_subscribers: list = []
_log_file = None


def _setup_file_log():
    global _log_file
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs")
    os.makedirs(log_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    _log_file = open(os.path.join(log_dir, f"session_{ts}.log"), "w", encoding="utf-8")


def subscribe(callback):
    """Register a callable(level, message) to receive log events."""
    with _lock:
        _subscribers.append(callback)


def unsubscribe(callback):
    with _lock:
        if callback in _subscribers:
            _subscribers.remove(callback)


def _emit(level: str, msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    with _lock:
        if _log_file:
            _log_file.write(line + "\n")
            _log_file.flush()
        for cb in list(_subscribers):
            try:
                cb(level, line)
            except Exception:
                pass


def info(msg: str):    _emit("INFO", msg)
def warn(msg: str):    _emit("WARN", msg)
def error(msg: str):   _emit("ERROR", msg)
def success(msg: str): _emit("OK", msg)
def debug(msg: str):   _emit("DEBUG", msg)


_setup_file_log()
