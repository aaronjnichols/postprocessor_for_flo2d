"""
FLO-2D Postprocessor QGIS Plugin - Dialog.

Professional dialog with native QGIS widgets, progress tracking,
detailed log output, and auto-loading of results into QGIS.
"""

import json
import os
import time

from qgis.PyQt.QtCore import Qt, QSettings, QSize
from qgis.PyQt.QtGui import QColor, QFont, QIcon, QTextCharFormat
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QAbstractItemView,
)
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsProject,
    QgsRasterLayer,
    QgsVectorLayer,
)
from qgis.gui import QgsProjectionSelectionWidget

from .output_discovery import get_vector_output_dirs
from .project_root import ensure_project_root_on_path
from .processing_worker import ProcessingWorker

_FALLBACK_PROJECT_MARKERS = (
    "CADPTS.DAT",
    "TOPO.DAT",
    "FPLAIN.DAT",
    "MANNINGS_N.DAT",
    "DEPTH.OUT",
    "CHAN.DAT",
    "INFLOW.DAT",
    "SWMM.inp",
)


def _load_supported_file_helpers():
    """Load registry helpers after bootstrapping the repo root onto sys.path."""
    project_root, _ = ensure_project_root_on_path(__file__)
    if project_root is None:
        return None, None
    try:
        from core.supported_files import (
            describe_project_marker_examples,
            list_present_validation_marker_files,
        )
    except ImportError:
        return None, None
    return describe_project_marker_examples, list_present_validation_marker_files


def _describe_project_markers() -> str:
    """Return short sample text for folder-validation messages."""
    describe_helper, _ = _load_supported_file_helpers()
    if describe_helper is None:
        return ", ".join((*_FALLBACK_PROJECT_MARKERS[:4], "..."))
    return describe_helper()


def _list_present_project_markers(folder: str) -> list[str]:
    """Return supported marker files found in a project folder."""
    _, list_helper = _load_supported_file_helpers()
    if list_helper is None:
        return [
            filename
            for filename in _FALLBACK_PROJECT_MARKERS
            if os.path.isfile(os.path.join(folder, filename))
        ]
    return list_helper(folder)


class Flo2dPostprocessorDialog(QDialog):
    """Main dialog for the FLO-2D Postprocessor plugin."""

    SETTINGS_KEY = "Flo2dPostprocessor"

    def __init__(self, iface, parent=None):
        super().__init__(parent or iface.mainWindow())
        self.iface = iface
        self.worker = None
        self._start_time = None

        self.setWindowTitle("FLO-2D Postprocessor")
        self.setMinimumSize(720, 780)
        self.resize(780, 900)
        self.setWindowFlags(
            self.windowFlags() | Qt.WindowMinMaxButtonsHint
        )

        self._build_ui()
        self._restore_settings()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        """Construct all widgets and lay them out."""
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        # --- Header ---
        header = QLabel(
            "<b style='font-size:14pt;'>FLO-2D Postprocessor</b>"
            "<br><span style='color:#888;'>Extract, process, and visualize FLO-2D results</span>"
        )
        header.setAlignment(Qt.AlignLeft)
        root.addWidget(header)

        # Horizontal line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        root.addWidget(line)

        # Use a splitter so the user can resize the log area
        splitter = QSplitter(Qt.Vertical)
        root.addWidget(splitter, 1)

        # --- Top panel (settings) ---
        settings_widget = QWidget()
        settings_layout = QVBoxLayout(settings_widget)
        settings_layout.setContentsMargins(0, 0, 0, 0)
        settings_layout.setSpacing(6)
        splitter.addWidget(settings_widget)

        # 1) Project Folders
        folders_group = QGroupBox("FLO-2D Project Folders")
        folders_vbox = QVBoxLayout(folders_group)
        folders_vbox.setSpacing(4)

        self.folder_list = QListWidget()
        self.folder_list.setAlternatingRowColors(True)
        self.folder_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.folder_list.setMinimumHeight(80)
        self.folder_list.setMaximumHeight(140)
        self.folder_list.setToolTip(
            "FLO-2D project directories to process.\n"
            f"Each directory should contain supported files such as {_describe_project_markers()}."
        )
        folders_vbox.addWidget(self.folder_list)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        self.btn_add_folder = QPushButton("Add Folder...")
        self.btn_add_folder.setToolTip("Browse for a FLO-2D project folder")
        self.btn_add_folder.clicked.connect(self._add_folder)
        btn_row.addWidget(self.btn_add_folder)

        self.btn_remove_folder = QPushButton("Remove Selected")
        self.btn_remove_folder.setToolTip("Remove highlighted folders from the list")
        self.btn_remove_folder.clicked.connect(self._remove_folders)
        btn_row.addWidget(self.btn_remove_folder)

        self.btn_clear_folders = QPushButton("Clear All")
        self.btn_clear_folders.setToolTip("Remove all folders from the list")
        self.btn_clear_folders.clicked.connect(self._clear_folders)
        btn_row.addWidget(self.btn_clear_folders)
        btn_row.addStretch()
        folders_vbox.addLayout(btn_row)
        settings_layout.addWidget(folders_group)

        # 2) Settings grid: CRS, output format, style folder, options
        options_group = QGroupBox("Processing Options")
        grid = QGridLayout(options_group)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)
        row = 0

        # CRS selector
        grid.addWidget(QLabel("Coordinate Reference System:"), row, 0)
        self.crs_selector = QgsProjectionSelectionWidget()
        self.crs_selector.setToolTip(
            "Choose the CRS that matches your FLO-2D model.\n"
            "Click the globe icon to search by name or EPSG code."
        )
        default_crs = QgsCoordinateReferenceSystem("EPSG:2224")
        self.crs_selector.setCrs(default_crs)
        grid.addWidget(self.crs_selector, row, 1)
        row += 1

        # Output format
        grid.addWidget(QLabel("Vector Output Format:"), row, 0)
        self.combo_format = QComboBox()
        self.combo_format.addItems(["GeoPackage", "Shapefile"])
        self.combo_format.setToolTip(
            "GeoPackage (.gpkg) is recommended for modern workflows.\n"
            "Shapefile (.shp) for legacy compatibility."
        )
        grid.addWidget(self.combo_format, row, 1)
        row += 1

        # Style folder
        grid.addWidget(QLabel("QML Style Folder (optional):"), row, 0)
        style_row = QHBoxLayout()
        self.txt_style_folder = QLineEdit()
        self.txt_style_folder.setPlaceholderText("No style folder selected")
        self.txt_style_folder.setReadOnly(True)
        self.txt_style_folder.setToolTip(
            "Folder containing .qml style files.\n"
            "If provided, styles are copied next to output layers for automatic styling."
        )
        style_row.addWidget(self.txt_style_folder)
        btn_browse_style = QToolButton()
        btn_browse_style.setText("...")
        btn_browse_style.setToolTip("Browse for style folder")
        btn_browse_style.clicked.connect(self._browse_style_folder)
        style_row.addWidget(btn_browse_style)
        btn_clear_style = QToolButton()
        btn_clear_style.setText("x")
        btn_clear_style.setToolTip("Clear style folder")
        btn_clear_style.clicked.connect(lambda: self.txt_style_folder.clear())
        style_row.addWidget(btn_clear_style)
        grid.addLayout(style_row, row, 1)
        row += 1

        # Checkboxes row
        checks_row = QHBoxLayout()
        self.chk_create_points = QCheckBox("Create FLO-2D grid points layer")
        self.chk_create_points.setChecked(True)
        self.chk_create_points.setToolTip(
            "Generate a point layer with flow direction for every grid element.\n"
            "Disable for faster processing if not needed."
        )
        checks_row.addWidget(self.chk_create_points)

        self.chk_auto_load = QCheckBox("Auto-load results into QGIS")
        self.chk_auto_load.setChecked(True)
        self.chk_auto_load.setToolTip(
            "Automatically add output layers (vectors and rasters)\n"
            "to the current QGIS project in organized layer groups."
        )
        checks_row.addWidget(self.chk_auto_load)

        self.chk_verbose = QCheckBox("Verbose logging")
        self.chk_verbose.setChecked(False)
        self.chk_verbose.setToolTip("Show detailed debug messages in the log panel.")
        checks_row.addWidget(self.chk_verbose)
        checks_row.addStretch()
        grid.addLayout(checks_row, row, 0, 1, 2)
        settings_layout.addWidget(options_group)

        # --- Bottom panel (progress + log) ---
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(6)
        splitter.addWidget(bottom_widget)

        # Progress section
        progress_group = QGroupBox("Progress")
        progress_vbox = QVBoxLayout(progress_group)
        progress_vbox.setSpacing(4)

        self.lbl_status = QLabel("Ready")
        self.lbl_status.setStyleSheet("font-weight: bold;")
        progress_vbox.addWidget(self.lbl_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p% complete")
        progress_vbox.addWidget(self.progress_bar)

        self.lbl_detail = QLabel("")
        self.lbl_detail.setStyleSheet("color: #666;")
        progress_vbox.addWidget(self.lbl_detail)
        bottom_layout.addWidget(progress_group)

        # Log panel
        log_group = QGroupBox("Processing Log")
        log_vbox = QVBoxLayout(log_group)
        log_vbox.setSpacing(4)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        self.log_text.setMinimumHeight(120)
        self.log_text.setToolTip("Detailed processing log messages")
        log_vbox.addWidget(self.log_text)

        log_btn_row = QHBoxLayout()
        btn_clear_log = QPushButton("Clear Log")
        btn_clear_log.clicked.connect(self.log_text.clear)
        log_btn_row.addWidget(btn_clear_log)
        log_btn_row.addStretch()
        self.lbl_elapsed = QLabel("")
        self.lbl_elapsed.setStyleSheet("color: #888;")
        log_btn_row.addWidget(self.lbl_elapsed)
        log_vbox.addLayout(log_btn_row)
        bottom_layout.addWidget(log_group, 1)

        # Set sensible splitter proportions (40% settings, 60% log)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 6)

        # --- Action buttons ---
        line2 = QFrame()
        line2.setFrameShape(QFrame.HLine)
        line2.setFrameShadow(QFrame.Sunken)
        root.addWidget(line2)

        action_row = QHBoxLayout()
        action_row.setSpacing(8)

        self.btn_run = QPushButton("  Run Postprocessor  ")
        self.btn_run.setMinimumHeight(36)
        self.btn_run.setStyleSheet(
            "QPushButton {"
            "  background-color: #2a7ae2; color: white; font-weight: bold;"
            "  border-radius: 4px; padding: 6px 20px;"
            "}"
            "QPushButton:hover { background-color: #1a6ad4; }"
            "QPushButton:disabled { background-color: #888; }"
        )
        self.btn_run.setToolTip("Start processing all listed FLO-2D projects (Ctrl+R)")
        self.btn_run.clicked.connect(self._start_processing)
        action_row.addWidget(self.btn_run)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setMinimumHeight(36)
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.setToolTip("Cancel the current processing run")
        self.btn_cancel.clicked.connect(self._cancel_processing)
        action_row.addWidget(self.btn_cancel)

        action_row.addStretch()

        btn_close = QPushButton("Close")
        btn_close.setMinimumHeight(36)
        btn_close.clicked.connect(self.close)
        action_row.addWidget(btn_close)

        root.addLayout(action_row)

    # ------------------------------------------------------------------
    # Folder management
    # ------------------------------------------------------------------

    def _add_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select FLO-2D Project Folder", "", QFileDialog.ShowDirsOnly
        )
        if not folder:
            return

        # Check for duplicates
        for i in range(self.folder_list.count()):
            if self.folder_list.item(i).data(Qt.UserRole) == folder:
                self._log_message("Folder already in list: " + folder, "warning")
                return

        # Validate it looks like a FLO-2D folder
        found = _list_present_project_markers(folder)
        if not found:
            reply = QMessageBox.question(
                self,
                "Folder Validation",
                f"This folder does not appear to contain FLO-2D files:\n\n"
                f"{folder}\n\n"
                f"No supported FLO-2D files ({_describe_project_markers()}) were found.\n\n"
                f"Add it anyway?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

        # Build a descriptive list item
        basename = os.path.basename(folder)
        file_count = len(found)
        item = QListWidgetItem()
        item.setText(f"{basename}   ({file_count} FLO-2D files found)")
        item.setData(Qt.UserRole, folder)
        item.setToolTip(folder)
        self.folder_list.addItem(item)
        self._save_settings()

    def _remove_folders(self):
        for item in self.folder_list.selectedItems():
            self.folder_list.takeItem(self.folder_list.row(item))
        self._save_settings()

    def _clear_folders(self):
        self.folder_list.clear()
        self._save_settings()

    def _browse_style_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select QML Style Folder", "", QFileDialog.ShowDirsOnly
        )
        if folder:
            self.txt_style_folder.setText(folder)
            self._save_settings()

    # ------------------------------------------------------------------
    # Processing
    # ------------------------------------------------------------------

    def _validate_inputs(self):
        """Validate inputs and return a list of error strings (empty = valid)."""
        errors = []
        if self.folder_list.count() == 0:
            errors.append("Add at least one FLO-2D project folder.")

        crs = self.crs_selector.crs()
        if not crs.isValid():
            errors.append("Select a valid Coordinate Reference System.")

        style = self.txt_style_folder.text().strip()
        if style and not os.path.isdir(style):
            errors.append(f"Style folder does not exist: {style}")

        # Check folders still exist
        for i in range(self.folder_list.count()):
            folder = self.folder_list.item(i).data(Qt.UserRole)
            if not os.path.isdir(folder):
                errors.append(f"Folder no longer exists: {folder}")

        return errors

    def _start_processing(self):
        errors = self._validate_inputs()
        if errors:
            QMessageBox.warning(
                self, "Validation Errors", "\n\n".join(errors)
            )
            return

        # Collect parameters
        folders = []
        for i in range(self.folder_list.count()):
            folders.append(self.folder_list.item(i).data(Qt.UserRole))

        crs = self.crs_selector.crs()
        epsg = crs.postgisSrid()

        output_format = self.combo_format.currentText()
        style_folder = self.txt_style_folder.text().strip() or None
        create_points = self.chk_create_points.isChecked()
        verbose = self.chk_verbose.isChecked()

        # Prepare UI
        self.log_text.clear()
        self.progress_bar.setValue(0)
        self.lbl_status.setText("Starting...")
        self.lbl_detail.setText("")
        self.lbl_elapsed.setText("")
        self._set_running_state(True)
        self._start_time = time.time()

        self._log_message("=" * 60, "info")
        self._log_message("FLO-2D Postprocessor started", "info")
        self._log_message(f"CRS: EPSG:{epsg}  |  Format: {output_format}", "info")
        self._log_message(f"Folders: {len(folders)}", "info")
        self._log_message("=" * 60, "info")

        # Ensure postprocessor project root is importable.
        project_root, _ = ensure_project_root_on_path(__file__)
        if project_root is None:
            QMessageBox.critical(
                self,
                "Import Configuration Error",
                "Failed to locate FLO-2D postprocessor project root.\n\n"
                "Run scripts/install_qgis_plugin.bat and restart QGIS.",
            )
            self._set_running_state(False)
            return

        # Launch worker thread
        self.worker = ProcessingWorker(
            folders=folders,
            epsg=epsg,
            output_format=output_format,
            create_points=create_points,
            verbose=verbose,
            style_folder=style_folder,
        )
        self.worker.log_message.connect(self._on_worker_log)
        self.worker.progress_updated.connect(self._on_worker_progress)
        self.worker.folder_started.connect(self._on_folder_started)
        self.worker.folder_finished.connect(self._on_folder_finished)
        self.worker.processing_finished.connect(self._on_processing_finished)
        self.worker.processing_error.connect(self._on_processing_error)
        self.worker.start()

    def _cancel_processing(self):
        if self.worker and self.worker.isRunning():
            self._log_message("Cancellation requested...", "warning")
            self.worker.cancel()

    def _set_running_state(self, running):
        """Toggle UI elements between running and idle states."""
        self.btn_run.setEnabled(not running)
        self.btn_cancel.setEnabled(running)
        self.btn_add_folder.setEnabled(not running)
        self.btn_remove_folder.setEnabled(not running)
        self.btn_clear_folders.setEnabled(not running)
        self.crs_selector.setEnabled(not running)
        self.combo_format.setEnabled(not running)
        self.chk_create_points.setEnabled(not running)
        self.chk_auto_load.setEnabled(not running)
        self.chk_verbose.setEnabled(not running)

    # ------------------------------------------------------------------
    # Worker signal handlers
    # ------------------------------------------------------------------

    def _on_worker_log(self, message, level):
        self._log_message(message, level)

    def _on_worker_progress(self, percent, detail):
        self.progress_bar.setValue(percent)
        self.lbl_detail.setText(detail)
        if self._start_time:
            elapsed = time.time() - self._start_time
            self.lbl_elapsed.setText(self._format_elapsed(elapsed))

    def _on_folder_started(self, folder_path, index, total):
        name = os.path.basename(folder_path)
        self.lbl_status.setText(f"Processing folder {index}/{total}: {name}")
        self._log_message(f"--- Folder {index}/{total}: {name} ---", "info")

    def _on_folder_finished(self, folder_path, index, total):
        name = os.path.basename(folder_path)
        self._log_message(f"Completed: {name}", "success")

    def _on_processing_finished(self, results):
        elapsed = time.time() - self._start_time if self._start_time else 0
        self._set_running_state(False)
        self.progress_bar.setValue(100)
        self.lbl_status.setText("Completed successfully")
        self.lbl_detail.setText(
            f"{len(results)} folder(s) processed in {self._format_elapsed(elapsed)}"
        )
        self._log_message("=" * 60, "success")
        self._log_message(
            f"All processing complete  ({self._format_elapsed(elapsed)})", "success"
        )
        self._log_message("=" * 60, "success")

        # Auto-load results into QGIS
        if self.chk_auto_load.isChecked():
            for folder_path in results:
                self._load_results_into_qgis(folder_path)

        self._save_settings()

    def _on_processing_error(self, error_msg):
        elapsed = time.time() - self._start_time if self._start_time else 0
        self._set_running_state(False)
        self.lbl_status.setText("Processing failed")
        self.lbl_detail.setText(f"Failed after {self._format_elapsed(elapsed)}")
        self._log_message(f"ERROR: {error_msg}", "error")
        QMessageBox.critical(
            self,
            "Processing Error",
            f"An error occurred during processing:\n\n{error_msg}",
        )

    # ------------------------------------------------------------------
    # Auto-load results into QGIS
    # ------------------------------------------------------------------

    def _load_results_into_qgis(self, project_folder):
        """Load output layers into QGIS organized in layer groups."""
        project = QgsProject.instance()
        root = project.layerTreeRoot()
        folder_name = os.path.basename(project_folder)

        # Create a top-level group for this FLO-2D project
        main_group = root.insertGroup(0, f"FLO-2D: {folder_name}")

        existing_vector_dirs = get_vector_output_dirs(project_folder)
        raster_dir = os.path.join(project_folder, "flo2d_rasters")

        # Load vector layers
        if existing_vector_dirs:
            vector_group = main_group.addGroup("Vector Layers")
            loaded = 0
            seen_vector_paths = set()
            for vector_dir in existing_vector_dirs:
                vector_files = sorted(os.listdir(vector_dir))
                for f in vector_files:
                    if not f.lower().endswith((".gpkg", ".shp")):
                        continue

                    full_path = os.path.join(vector_dir, f)
                    normalized_path = os.path.normcase(os.path.abspath(full_path))
                    if normalized_path in seen_vector_paths:
                        continue
                    seen_vector_paths.add(normalized_path)

                    layer_name = os.path.splitext(f)[0]
                    layer = QgsVectorLayer(full_path, layer_name, "ogr")
                    if layer.isValid():
                        project.addMapLayer(layer, False)
                        vector_group.addLayer(layer)
                        loaded += 1
            self._log_message(
                f"Loaded {loaded} vector layer(s) into QGIS from "
                f"{len(existing_vector_dirs)} folder(s)",
                "info",
            )

        # Load raster layers
        if os.path.isdir(raster_dir):
            raster_group = main_group.addGroup("Raster Layers")
            raster_files = sorted(os.listdir(raster_dir))
            loaded = 0
            for f in raster_files:
                if f.endswith(".tif"):
                    full_path = os.path.join(raster_dir, f)
                    layer = QgsRasterLayer(full_path, os.path.splitext(f)[0])
                    if layer.isValid():
                        project.addMapLayer(layer, False)
                        raster_group.addLayer(layer)
                        loaded += 1
            self._log_message(f"Loaded {loaded} raster layer(s) into QGIS", "info")

        # Collapse the group initially to keep the layer panel tidy
        main_group.setExpanded(True)

        self._log_message(
            f"Results loaded into layer group 'FLO-2D: {folder_name}'", "success"
        )

    # ------------------------------------------------------------------
    # Logging helpers
    # ------------------------------------------------------------------

    LOG_COLORS = {
        "info": "#cccccc",
        "success": "#4caf50",
        "warning": "#ff9800",
        "error": "#f44336",
        "processing": "#2196f3",
        "discovery": "#9e9e9e",
    }

    def _log_message(self, message, level="info"):
        """Append a color-coded message to the log panel."""
        color = self.LOG_COLORS.get(level, "#cccccc")
        timestamp = time.strftime("%H:%M:%S")
        prefix_map = {
            "info": "INFO",
            "success": " OK ",
            "warning": "WARN",
            "error": "ERR ",
            "processing": "PROC",
            "discovery": "SCAN",
        }
        prefix = prefix_map.get(level, "INFO")
        html = (
            f"<span style='color:#888;'>{timestamp}</span> "
            f"<span style='color:{color};'>[{prefix}]</span> "
            f"<span style='color:{color};'>{message}</span>"
        )
        self.log_text.append(html)

    @staticmethod
    def _format_elapsed(seconds):
        if seconds < 60:
            return f"{seconds:.1f}s"
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        if minutes < 60:
            return f"{minutes}m {secs}s"
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours}h {mins}m {secs}s"

    # ------------------------------------------------------------------
    # Settings persistence
    # ------------------------------------------------------------------

    def _save_settings(self):
        s = QSettings()
        s.beginGroup(self.SETTINGS_KEY)

        folders = []
        for i in range(self.folder_list.count()):
            folders.append(self.folder_list.item(i).data(Qt.UserRole))
        s.setValue("folders", json.dumps(folders))
        s.setValue("crs_authid", self.crs_selector.crs().authid())
        s.setValue("output_format", self.combo_format.currentText())
        s.setValue("style_folder", self.txt_style_folder.text())
        s.setValue("create_points", self.chk_create_points.isChecked())
        s.setValue("auto_load", self.chk_auto_load.isChecked())
        s.setValue("verbose", self.chk_verbose.isChecked())
        s.endGroup()

    def _restore_settings(self):
        s = QSettings()
        s.beginGroup(self.SETTINGS_KEY)

        # Folders
        folders_json = s.value("folders", "[]")
        try:
            folders = json.loads(folders_json)
        except (json.JSONDecodeError, TypeError):
            folders = []
        for folder in folders:
            if os.path.isdir(folder):
                found = _list_present_project_markers(folder)
                basename = os.path.basename(folder)
                item = QListWidgetItem()
                item.setText(f"{basename}   ({len(found)} FLO-2D files found)")
                item.setData(Qt.UserRole, folder)
                item.setToolTip(folder)
                self.folder_list.addItem(item)

        # CRS
        authid = s.value("crs_authid", "EPSG:2224")
        crs = QgsCoordinateReferenceSystem(authid)
        if crs.isValid():
            self.crs_selector.setCrs(crs)

        # Output format
        fmt = s.value("output_format", "GeoPackage")
        idx = self.combo_format.findText(fmt)
        if idx >= 0:
            self.combo_format.setCurrentIndex(idx)

        # Style folder
        style = s.value("style_folder", "")
        if style:
            self.txt_style_folder.setText(style)

        # Checkboxes
        self.chk_create_points.setChecked(
            s.value("create_points", True, type=bool)
        )
        self.chk_auto_load.setChecked(
            s.value("auto_load", True, type=bool)
        )
        self.chk_verbose.setChecked(
            s.value("verbose", False, type=bool)
        )
        s.endGroup()

    def closeEvent(self, event):
        self._save_settings()
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self,
                "Processing in Progress",
                "Processing is still running. Cancel and close?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                self.worker.cancel()
                self.worker.wait(5000)
                event.accept()
            else:
                event.ignore()
                return
        event.accept()
