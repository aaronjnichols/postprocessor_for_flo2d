"""
FLO-2D Postprocessor QGIS Plugin - Background processing worker.

Runs the heavy postprocessing in a QThread so the QGIS UI stays responsive.
Emits signals for progress, log messages, and completion/error.
"""

import os
import sys
import time
import traceback

from qgis.PyQt.QtCore import QThread, pyqtSignal


class _WorkerTimingLogger:
    """TimingLogger-compatible adapter that emits Qt signals instead of logging."""

    def __init__(self, worker):
        self._worker = worker
        self.start_time = time.time()
        self.last_log_time = self.start_time

    def log(self, message):
        current = time.time()
        elapsed = current - self.last_log_time
        total = current - self.start_time
        self.last_log_time = current

        # Clean up technical suffix if present
        clean = message.split(" (Step ")[0] if " (Step " in message else message

        # Infer log level from message content
        level = self._infer_level(clean)
        self._worker.log_message.emit(clean, level)

    @staticmethod
    def _infer_level(msg):
        m = msg.lower()
        if any(k in m for k in ("error", "failed")):
            return "error"
        if "warning" in m:
            return "warning"
        if any(k in m for k in ("completed", "created", "successfully", "===")):
            return "success"
        if any(
            k in m
            for k in (
                "extracting", "creating", "initiating", "converting",
                "generating", "processing", "calculating", "applying",
                "scanning",
            )
        ):
            return "processing"
        return "info"


class ProcessingWorker(QThread):
    """Background thread for running FLO-2D postprocessing."""

    # Signals
    log_message = pyqtSignal(str, str)          # message, level
    progress_updated = pyqtSignal(int, str)     # percent (0-100), detail text
    folder_started = pyqtSignal(str, int, int)  # folder_path, 1-based index, total
    folder_finished = pyqtSignal(str, int, int)
    processing_finished = pyqtSignal(list)      # list of successfully processed folders
    processing_error = pyqtSignal(str)          # error message

    def __init__(
        self,
        folders,
        epsg,
        output_format="GeoPackage",
        create_points=True,
        verbose=False,
        style_folder=None,
        parent=None,
    ):
        super().__init__(parent)
        self.folders = list(folders)
        self.epsg = epsg
        self.output_format = output_format
        self.create_points = create_points
        self.verbose = verbose
        self.style_folder = style_folder
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        """Main worker loop - processes each folder sequentially."""
        # Ensure the project root is on sys.path so imports work
        plugin_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(plugin_dir)
        if project_root not in sys.path:
            sys.path.insert(0, project_root)

        try:
            from main import process_flo2d
        except ImportError as exc:
            self.processing_error.emit(
                f"Failed to import postprocessor: {exc}\n"
                f"Ensure the plugin is installed in the project root directory."
            )
            return

        total = len(self.folders)
        completed_folders = []

        for idx, folder in enumerate(self.folders, 1):
            if self._cancelled:
                self.log_message.emit("Processing cancelled by user.", "warning")
                break

            self.folder_started.emit(folder, idx, total)

            # Update overall progress (per-folder granularity)
            base_pct = int(((idx - 1) / total) * 100)
            self.progress_updated.emit(
                base_pct,
                f"Folder {idx}/{total}: {os.path.basename(folder)}",
            )

            timing_logger = _WorkerTimingLogger(self)

            try:
                result = process_flo2d(
                    file_path=folder,
                    coord_system=self.epsg,
                    create_flo2d_points=self.create_points,
                    verbose=self.verbose,
                    style_folder=self.style_folder,
                    output_format=self.output_format,
                    timing_logger=timing_logger,
                )
                completed_folders.append(folder)
                self.folder_finished.emit(folder, idx, total)
            except Exception as exc:
                tb = traceback.format_exc()
                self.log_message.emit(
                    f"Error processing {os.path.basename(folder)}: {exc}", "error"
                )
                self.log_message.emit(tb, "error")
                # Continue with next folder instead of aborting everything
                continue

        if self._cancelled:
            self.processing_error.emit("Processing was cancelled.")
        else:
            self.processing_finished.emit(completed_folders)
