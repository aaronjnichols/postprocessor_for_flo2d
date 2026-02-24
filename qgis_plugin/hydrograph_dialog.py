"""FLO-2D QGIS plugin popup dialog for time-series hydrographs."""

import numpy as np
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
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
            series (list[dict]): dict keys: x, y, label, color.
            stats (list[tuple]): tuple keys: label, value.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(780, 580)
        self.setAttribute(Qt.WA_DeleteOnClose)

        self._series = self._normalize_series(series)
        self._colors = [_resolve_color(s["color"], i) for i, s in enumerate(self._series)]
        self._interactive_enabled = False

        self._max_markers = []
        self._max_labels = []
        self._cursor_dots = []
        self._cursor_vline = None
        self._cursor_annot = None

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
        self._draw_plot()
        self._setup_cursor()
        layout.addWidget(self.canvas)

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

        self._apply_mode_visibility()

    # ------------------------------------------------------------------
    # Normalization and header
    # ------------------------------------------------------------------

    def _normalize_series(self, series):
        """Normalize incoming series into consistent numeric arrays."""
        normalized = []
        for i, item in enumerate(series):
            x = np.asarray(item.get("x", []), dtype=float)
            y = np.asarray(item.get("y", []), dtype=float)
            count = min(len(x), len(y))
            if count == 0:
                continue
            normalized.append(
                {
                    "x": x[:count],
                    "y": y[:count],
                    "label": str(item.get("label", f"Series {i + 1}")),
                    "color": str(item.get("color", "")),
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

    # ------------------------------------------------------------------
    # Plot
    # ------------------------------------------------------------------

    def _draw_plot(self):
        ax = self.ax
        ax.clear()

        for i, series in enumerate(self._series):
            ax.plot(
                series["x"],
                series["y"],
                color=self._colors[i],
                linewidth=1.8,
                label=series["label"],
                zorder=2,
            )

        ax.set_xlabel("Time (hours)")
        if len(self._series) == 1:
            ax.set_ylabel(self._series[0]["label"])
        elif len(self._series) > 1:
            ax.set_ylabel("Value")
        ax.grid(True, color=_GRID, linewidth=0.8)
        ax.margins(x=0.02)

        if len(self._series) > 1:
            ax.legend(loc="upper right", fontsize=9)

        self._create_peak_annotations()

    def _create_peak_annotations(self):
        """Create max-mode markers and text labels for each series."""
        self._max_markers = []
        self._max_labels = []
        multi_series = len(self._series) > 1

        for i, series in enumerate(self._series):
            x = series["x"]
            y = series["y"]
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
                color=self._colors[i],
                markersize=6,
                zorder=4,
            )
            self._max_markers.append(marker)

            label_text = _format_max_label(
                series["label"],
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
                color=self._colors[i],
                zorder=5,
            )
            self._max_labels.append(label)

    # ------------------------------------------------------------------
    # Interactive cursor
    # ------------------------------------------------------------------

    def _setup_cursor(self):
        self._cursor_vline = self.ax.axvline(
            x=0,
            color=_CURSOR,
            linestyle="--",
            linewidth=0.9,
            visible=False,
            zorder=6,
        )

        self._cursor_dots = []
        for i in range(len(self._series)):
            dot, = self.ax.plot(
                [],
                [],
                "o",
                color=self._colors[i],
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

        self.canvas.mpl_connect("motion_notify_event", self._on_mouse_move)

    def _hide_cursor(self):
        """Hide all hover-mode artists."""
        if self._cursor_vline is not None:
            self._cursor_vline.set_visible(False)
        for dot in self._cursor_dots:
            dot.set_visible(False)
        if self._cursor_annot is not None:
            self._cursor_annot.set_visible(False)

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
        if show_max:
            self._hide_cursor()

    def _on_mouse_move(self, event):
        if not self._interactive_enabled or not self._series:
            return

        if event.inaxes is not self.ax or event.xdata is None:
            self._hide_cursor()
            self.canvas.draw_idle()
            return

        x_ref = self._series[0]["x"]
        idx_ref = _nearest_valid_index(x_ref, float(event.xdata))
        if idx_ref is None:
            return
        snap_x = float(x_ref[idx_ref])

        lines = [f"Time: {snap_x:.2f} hr"]
        anchor_point = None

        self._cursor_vline.set_xdata([snap_x, snap_x])
        self._cursor_vline.set_visible(True)

        for i, series in enumerate(self._series):
            idx = _nearest_valid_index(series["x"], snap_x)
            if idx is None:
                lines.append(f"{series['label']}: N/A")
                self._cursor_dots[i].set_visible(False)
                continue

            px = float(series["x"][idx])
            py = float(series["y"][idx])
            if not np.isfinite(py):
                lines.append(f"{series['label']}: N/A")
                self._cursor_dots[i].set_visible(False)
                continue

            lines.append(f"{series['label']}: {_fmt_value(py)}")
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
