"""FLO-2D QGIS plugin popup dialog for time-series hydrographs."""

import numpy as np
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

try:
    from matplotlib.backends.backend_qtagg import (
        FigureCanvasQTAgg as FigureCanvas,
    )
except ImportError:
    from matplotlib.backends.backend_qt5agg import (
        FigureCanvasQTAgg as FigureCanvas,
    )
from matplotlib.figure import Figure

_GRID = "#d9d9d9"
_CURSOR = "#666666"

_COLOR_MAP = {
    "blue": "#1f77b4",
    "red": "#d62728",
    "orange": "#ff7f0e",
    "green": "#2ca02c",
    "purple": "#9467bd",
}
_PALETTE = ["#1f77b4", "#ff7f0e", "#2ca02c", "#9467bd"]


def _resolve_color(color_str, index=0):
    """Resolve display color from a named or explicit value."""
    if color_str in _COLOR_MAP:
        return _COLOR_MAP[color_str]
    if color_str and color_str.startswith("#"):
        return color_str
    return _PALETTE[index % len(_PALETTE)]


def _format_max_label(series_label, peak_x, peak_y, include_series=False):
    """Build a concise peak label for max-mode annotations."""
    prefix = f"{series_label}: " if include_series else ""
    return f"{prefix}Max {peak_y:,.2f} @ {peak_x:.2f} hr"


def _nearest_valid_index(x_values, target_x):
    """Return nearest index to target_x among finite x values, or None."""
    if x_values.size == 0:
        return None
    finite = np.isfinite(x_values)
    if not np.any(finite):
        return None
    valid_indices = np.where(finite)[0]
    nearest_pos = int(np.argmin(np.abs(x_values[valid_indices] - target_x)))
    return int(valid_indices[nearest_pos])


def _fmt_value(value):
    """Format numeric value for hover labels."""
    if value is None or not np.isfinite(value):
        return "N/A"
    return f"{value:,.2f}"


class HydrographDialog(QDialog):
    """Popup dialog that supports max-mode and hover interactive mode."""

    def __init__(self, title, series, stats, parent=None):
        """
        Args:
            title (str): Window title.
            series (list[dict]): dict keys include x, y, label, color, id, default_on.
            stats (list[tuple]): tuple keys: label, value.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(900, 600)
        self.setAttribute(Qt.WA_DeleteOnClose)

        self._series = self._normalize_series(series)
        self._series_checkboxes = {}
        self._interactive_enabled = False

        self._max_markers = []
        self._max_labels = []
        self._cursor_dots = []
        self._cursor_vline = None
        self._cursor_annot = None

        self._active_series_ids = {
            series_item["id"]
            for series_item in self._series
            if series_item["default_on"]
        }
        if not self._active_series_ids and self._series:
            self._active_series_ids.add(self._series[0]["id"])

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 12)
        layout.setSpacing(10)

        if stats:
            self._build_stats_header(layout, stats)

        fig = Figure(figsize=(7, 4), dpi=100)
        fig.subplots_adjust(left=0.09, right=0.97, top=0.95, bottom=0.12)
        self.canvas = FigureCanvas(fig)
        self.canvas.setMouseTracking(True)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.ax = fig.add_subplot(111)

        chart_row = QHBoxLayout()
        chart_row.setSpacing(10)
        chart_row.addWidget(self._build_series_selector_panel(), 0)
        chart_row.addWidget(self.canvas, 1)
        layout.addLayout(chart_row, 1)

        button_row = QHBoxLayout()
        self._interactive_btn = QPushButton("Interactive: Off")
        self._interactive_btn.setCheckable(True)
        self._interactive_btn.toggled.connect(self._on_interactive_toggled)
        button_row.addWidget(self._interactive_btn)
        button_row.addStretch()

        close_btn = QPushButton("Close")
        close_btn.setFixedWidth(90)
        close_btn.clicked.connect(self.close)
        button_row.addWidget(close_btn)
        layout.addLayout(button_row)

        self._draw_plot()
        self.canvas.mpl_connect("motion_notify_event", self._on_mouse_move)
        self._apply_mode_visibility()

    # ------------------------------------------------------------------
    # Normalization and header
    # ------------------------------------------------------------------

    def _normalize_series(self, series):
        """Normalize incoming series into consistent numeric arrays."""
        normalized = []
        used_ids = set()
        for i, item in enumerate(series):
            x = np.asarray(item.get("x", []), dtype=float)
            y = np.asarray(item.get("y", []), dtype=float)
            count = min(len(x), len(y))
            if count == 0:
                continue

            base_id = str(item.get("id", f"series_{i + 1}"))
            series_id = base_id
            suffix = 2
            while series_id in used_ids:
                series_id = f"{base_id}_{suffix}"
                suffix += 1
            used_ids.add(series_id)

            normalized.append(
                {
                    "id": series_id,
                    "x": x[:count],
                    "y": y[:count],
                    "label": str(item.get("label", f"Series {i + 1}")),
                    "color": _resolve_color(str(item.get("color", "")), i),
                    "default_on": bool(item.get("default_on", i == 0)),
                }
            )
        return normalized

    def _build_stats_header(self, parent_layout, stats):
        row = QHBoxLayout()
        row.setSpacing(18)

        for label_text, value_text in stats:
            cell = QVBoxLayout()
            cell.setSpacing(1)

            value_label = QLabel(str(value_text))
            value_label.setStyleSheet("font-size: 16px; font-weight: 600;")
            text_label = QLabel(label_text.rstrip(":"))
            text_label.setStyleSheet("font-size: 11px; color: #666666;")

            cell.addWidget(value_label)
            cell.addWidget(text_label)
            row.addLayout(cell)

        row.addStretch()
        parent_layout.addLayout(row)

    def _build_series_selector_panel(self):
        """Build checkbox controls for selecting visible time series."""
        panel = QGroupBox("Time Series")
        panel.setMinimumWidth(250)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setSpacing(6)

        for series_item in self._series:
            checkbox = QCheckBox(series_item["label"])
            checkbox.setProperty("series_id", series_item["id"])
            checkbox.setChecked(series_item["id"] in self._active_series_ids)
            checkbox.toggled.connect(self._on_series_checkbox_toggled)
            self._series_checkboxes[series_item["id"]] = checkbox
            panel_layout.addWidget(checkbox)

        panel_layout.addStretch()
        return panel

    # ------------------------------------------------------------------
    # Plot
    # ------------------------------------------------------------------

    def _get_visible_series(self):
        """Return series currently selected via checkboxes."""
        return [
            series_item
            for series_item in self._series
            if series_item["id"] in self._active_series_ids
        ]

    def _draw_plot(self):
        ax = self.ax
        ax.clear()

        visible_series = self._get_visible_series()

        if not visible_series:
            ax.set_xlabel("Time (hours)")
            ax.grid(True, color=_GRID, linewidth=0.8)
            ax.text(
                0.5,
                0.5,
                "Select at least one time series to display.",
                ha="center",
                va="center",
                transform=ax.transAxes,
                fontsize=10,
                color="#666666",
            )
            self._max_markers = []
            self._max_labels = []
            self._setup_cursor_artists([])
            return

        for series_item in visible_series:
            ax.plot(
                series_item["x"],
                series_item["y"],
                color=series_item["color"],
                linewidth=1.8,
                label=series_item["label"],
                zorder=2,
            )

        ax.set_xlabel("Time (hours)")
        if len(visible_series) == 1:
            ax.set_ylabel(visible_series[0]["label"])
        else:
            ax.set_ylabel("Value")
        ax.grid(True, color=_GRID, linewidth=0.8)
        ax.margins(x=0.02)

        if len(visible_series) > 1:
            ax.legend(loc="upper right", fontsize=9)

        self._create_peak_annotations(visible_series)
        self._setup_cursor_artists(visible_series)

    def _create_peak_annotations(self, visible_series):
        """Create max-mode markers and text labels for each visible series."""
        self._max_markers = []
        self._max_labels = []
        multi_series = len(visible_series) > 1

        for series_item in visible_series:
            x = series_item["x"]
            y = series_item["y"]
            finite = np.isfinite(x) & np.isfinite(y)
            if not np.any(finite):
                continue

            x_valid = x[finite]
            y_valid = y[finite]
            peak_idx = int(np.argmax(y_valid))
            peak_x = float(x_valid[peak_idx])
            peak_y = float(y_valid[peak_idx])

            marker, = self.ax.plot(
                [peak_x],
                [peak_y],
                "o",
                color=series_item["color"],
                markersize=6,
                zorder=4,
            )
            self._max_markers.append(marker)

            label_text = _format_max_label(
                series_item["label"],
                peak_x,
                peak_y,
                include_series=multi_series,
            )
            label = self.ax.annotate(
                label_text,
                xy=(peak_x, peak_y),
                xytext=(8, 6),
                textcoords="offset points",
                fontsize=8,
                color=series_item["color"],
                zorder=5,
            )
            self._max_labels.append(label)

    # ------------------------------------------------------------------
    # Interactive cursor
    # ------------------------------------------------------------------

    def _setup_cursor_artists(self, visible_series):
        """Create cursor artists for currently visible series."""
        self._cursor_vline = self.ax.axvline(
            x=0,
            color=_CURSOR,
            linestyle="--",
            linewidth=0.9,
            visible=False,
            zorder=6,
        )

        self._cursor_dots = []
        for series_item in visible_series:
            dot, = self.ax.plot(
                [],
                [],
                "o",
                color=series_item["color"],
                markersize=6,
                visible=False,
                zorder=7,
            )
            self._cursor_dots.append(dot)

        self._cursor_annot = self.ax.annotate(
            "",
            xy=(0, 0),
            xytext=(12, 12),
            textcoords="offset points",
            fontsize=8,
            bbox=dict(
                facecolor="white",
                alpha=0.95,
                edgecolor="#888888",
                boxstyle="round,pad=0.35",
            ),
            visible=False,
            zorder=8,
        )

    def _hide_cursor(self):
        """Hide all hover-mode artists."""
        if self._cursor_vline is not None:
            self._cursor_vline.set_visible(False)
        for dot in self._cursor_dots:
            dot.set_visible(False)
        if self._cursor_annot is not None:
            self._cursor_annot.set_visible(False)

    def _on_series_checkbox_toggled(self, checked):
        """Toggle line visibility based on user checkbox selection."""
        checkbox = self.sender()
        if checkbox is None:
            return
        series_id = checkbox.property("series_id")
        if not series_id:
            return

        if checked:
            self._active_series_ids.add(series_id)
        else:
            self._active_series_ids.discard(series_id)

        self._draw_plot()
        self._apply_mode_visibility()
        self.canvas.draw_idle()

    def _on_interactive_toggled(self, checked):
        """Switch between max mode and interactive hover mode."""
        self._interactive_enabled = bool(checked)
        self._interactive_btn.setText(
            "Interactive: On" if self._interactive_enabled else "Interactive: Off"
        )
        self._apply_mode_visibility()
        self.canvas.draw_idle()

    def _apply_mode_visibility(self):
        """Toggle max vs cursor artists based on current mode."""
        show_max = not self._interactive_enabled
        for marker in self._max_markers:
            marker.set_visible(show_max)
        for label in self._max_labels:
            label.set_visible(show_max)

        if show_max or not self._get_visible_series():
            self._hide_cursor()

    def _on_mouse_move(self, event):
        visible_series = self._get_visible_series()
        if not self._interactive_enabled or not visible_series:
            return

        if event.inaxes is not self.ax or event.xdata is None:
            self._hide_cursor()
            self.canvas.draw_idle()
            return

        x_ref = visible_series[0]["x"]
        idx_ref = _nearest_valid_index(x_ref, float(event.xdata))
        if idx_ref is None:
            return
        snap_x = float(x_ref[idx_ref])

        lines = [f"Time: {snap_x:.2f} hr"]
        anchor_point = None

        self._cursor_vline.set_xdata([snap_x, snap_x])
        self._cursor_vline.set_visible(True)

        for i, series_item in enumerate(visible_series):
            idx = _nearest_valid_index(series_item["x"], snap_x)
            if idx is None:
                lines.append(f"{series_item['label']}: N/A")
                if i < len(self._cursor_dots):
                    self._cursor_dots[i].set_visible(False)
                continue

            px = float(series_item["x"][idx])
            py = float(series_item["y"][idx])
            if not np.isfinite(py):
                lines.append(f"{series_item['label']}: N/A")
                if i < len(self._cursor_dots):
                    self._cursor_dots[i].set_visible(False)
                continue

            lines.append(f"{series_item['label']}: {_fmt_value(py)}")
            if i < len(self._cursor_dots):
                self._cursor_dots[i].set_data([px], [py])
                self._cursor_dots[i].set_visible(True)
            if anchor_point is None:
                anchor_point = (px, py)

        if anchor_point is None:
            self._hide_cursor()
            self.canvas.draw_idle()
            return

        self._cursor_annot.xy = anchor_point
        self._cursor_annot.set_text("\n".join(lines))
        self._cursor_annot.set_visible(True)
        self.canvas.draw_idle()
