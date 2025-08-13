from __future__ import annotations

"""
Simple, centralized messaging system for the FLO-2D GUI.

This module provides a single Messenger API and a small adapter that bridges the
existing `timing_logger` interface used by `main.process_flo2d` to the GUI.

Design goals:
- One message entry point (Messenger.send and helpers)
- Optional duplicate suppression and throttling
- Single Tk sink to write to the GUI safely via `after(0, ...)`
- A `TimingLoggerAdapter` that mirrors the `.log(message)` calls and updates
  progress via a callback compatible with the GUI's existing progress UI.
"""

import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional, Dict

try:
    import tkinter as tk
except Exception:  # pragma: no cover - allows CLI usage without Tk
    tk = None

# Reuse existing simple progress structure to minimize refactor for now
from .message_system import ProgressTracker


class Category(str, Enum):
    info = "info"
    success = "success"
    processing = "processing"
    warning = "warning"
    error = "error"
    file = "file"
    step = "step"
    discovery = "discovery"
    spatial = "spatial"
    validation = "validation"
    output = "output"


@dataclass
class Message:
    text: str
    category: Category = Category.info
    timestamp: float = time.time()


class DedupFilter:
    def __init__(self, window_seconds: float = 2.0):
        self.window_seconds = window_seconds
        self._history: Dict[str, float] = {}

    def allow(self, message: Message) -> bool:
        now = time.time()
        last = self._history.get(message.text)
        if last is not None and (now - last) < self.window_seconds:
            return False
        self._history[message.text] = now
        return True


class ThrottleFilter:
    def __init__(self, min_interval: float = 0.5):
        self.min_interval = min_interval
        self._last_sent: float = 0.0

    def allow(self, message: Message) -> bool:
        now = time.time()
        if (now - self._last_sent) < self.min_interval:
            return False
        self._last_sent = now
        return True


class TkSink:
    """Minimal sink that writes to the GUI `RichMessageFrame` safely."""

    def __init__(self, rich_message_frame):
        self.rich_message_frame = rich_message_frame

    def emit(self, message: Message) -> None:
        # Delegate formatting and styling to `RichMessageFrame.add_message`
        # Use Tk's thread-safe scheduling
        try:
            widget = self.rich_message_frame
            if hasattr(widget, 'after'):
                widget.after(0, lambda: self.rich_message_frame.add_message(message.text, message.category.value))
            else:  # Fallback (should not occur in GUI usage)
                self.rich_message_frame.add_message(message.text, message.category.value)
        except Exception:
            # Fail-safe: avoid crashing the process due to UI issues
            pass


class Messenger:
    def __init__(self, sink: TkSink, enable_dedup: bool = True, enable_throttle: bool = False):
        self.sink = sink
        self.dedup = DedupFilter() if enable_dedup else None
        self.throttle = ThrottleFilter() if enable_throttle else None

    def send(self, text: str, category: str | Category = Category.info) -> None:
        cat = Category(category) if not isinstance(category, Category) else category
        msg = Message(text=text, category=cat, timestamp=time.time())
        if self.dedup and not self.dedup.allow(msg):
            return
        if self.throttle and not self.throttle.allow(msg):
            return
        self.sink.emit(msg)

    # Convenience helpers
    def info(self, text: str) -> None: self.send(text, Category.info)
    def success(self, text: str) -> None: self.send(text, Category.success)
    def warning(self, text: str) -> None: self.send(text, Category.warning)
    def error(self, text: str) -> None: self.send(text, Category.error)
    def processing(self, text: str) -> None: self.send(text, Category.processing)
    def discovery(self, text: str) -> None: self.send(text, Category.discovery)


class TimingLoggerAdapter:
    """
    Adapter that presents a `.log(message)` method compatible with the existing
    `timing_logger` used in `main.process_flo2d`, but routes messages through
    the centralized Messenger and updates a simplified progress tracker.
    """

    def __init__(self, messenger: Messenger, progress_callback: Optional[Callable] = None):
        self.messenger = messenger
        self.progress_callback = progress_callback
        self.start_time = time.time()
        self.last_log_time = self.start_time
        self.progress_tracker = ProgressTracker()

        # Minimal step mapping (0-based indices); expand as needed
        self.step_mapping: Dict[str, int] = {
            "Creating necessary output directories": 0,
            "Extracting model data from FLO-2D files": 1,
            "Converting model data to GeoDataFrame for spatial processing": 2,
            "Generating computational domain polygon": 3,
        }

    def log(self, message: str, msg_type: str = 'processing') -> None:
        # Extract the portion before any timing suffix from older loggers
        clean_message = message.split(" (Step ")[0]

        # Determine category heuristically if not provided
        category = self._infer_category(clean_message, default=msg_type)
        self.messenger.send(clean_message, category)

        # Simple progress step handling
        if clean_message in self.step_mapping:
            step_index = self.step_mapping[clean_message]
            if step_index > self.progress_tracker.current_step - 1:
                self.progress_tracker.current_step = step_index + 1
                self.progress_tracker.current_step_progress = 0.0
                self.progress_tracker.set_current_operation(clean_message)
            if self.progress_callback:
                self.progress_callback(self.progress_tracker)
        else:
            if self.progress_tracker.current_step > 0:
                current = self.progress_tracker.current_step_progress
                if current < 0.9:
                    inc = max(0.05, (0.9 - current) * 0.2)
                    self.progress_tracker.current_step_progress = min(0.9, current + inc)
                    if self.progress_callback:
                        self.progress_callback(self.progress_tracker)

        self.last_log_time = time.time()

    def _infer_category(self, msg: str, default: str = 'processing') -> str:
        m = msg.lower()
        if any(k in m for k in ("error", "failed")):
            return Category.error.value
        if "warning" in m:
            return Category.warning.value
        if any(k in m for k in ("completed", "created", "successfully")):
            return Category.success.value
        if any(k in m for k in ("processing", "extracting", "creating", "initiating", "converting", "generating")):
            return Category.processing.value
        return default


