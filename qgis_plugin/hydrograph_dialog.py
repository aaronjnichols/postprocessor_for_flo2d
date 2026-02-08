"""
FLO-2D Postprocessor QGIS Plugin - Interactive time-series popup dialog.

Displays a configurable dark-mode plot (1 or 2 series) with gradient fill,
interactive hover cursor, and summary statistics.  Supports floodplain cross
sections, hydraulic structures, SWMM junctions, outfalls, and conduits.
"""

import numpy as np
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QWidget,
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

# ---------------------------------------------------------------------------
# Dark theme palette
# ---------------------------------------------------------------------------
_BG = "#0d1117"
_BG_CARD = "#161b22"
_TEXT = "#e6edf3"
_TEXT_MUTED = "#7d8590"
_GRID = "#21262d"
_BORDER = "#30363d"
_CURSOR = "#484f58"

# Map simple color names to dark-mode-friendly hex values
_COLOR_MAP = {
    "blue": "#2f81f7",
    "red": "#f47067",
    "orange": "#f0883e",
    "green": "#3fb950",
    "purple": "#a371f7",
}

# Fallback ordered palette when colors aren't specified
_PALETTE = ["#2f81f7", "#f0883e", "#3fb950", "#a371f7"]


def _resolve_color(color_str, index=0):
    """Map a color name to a dark-mode hex value."""
    if color_str in _COLOR_MAP:
        return _COLOR_MAP[color_str]
    if color_str and color_str.startswith("#"):
        return color_str
    return _PALETTE[index % len(_PALETTE)]


class HydrographDialog(QDialog):
    """Dark-mode popup dialog showing a time-series plot and statistics."""

    def __init__(self, title, series, stats, parent=None):
        """
        Args:
            title (str): Window title.
            series (list[dict]): Each dict has keys 'x', 'y', 'label', 'color'.
            stats (list[tuple]): Each tuple is (label_str, value_str).
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(780, 580)
        self.setAttribute(Qt.WA_DeleteOnClose)

        self._series = series
        self._colors = [_resolve_color(s.get("color", ""), i)
                        for i, s in enumerate(series)]

        self._apply_stylesheet()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(14)

        # --- Stats header ---
        if stats:
            self._build_stats_header(layout, stats)

        # --- Matplotlib canvas ---
        fig = Figure(figsize=(7, 4), dpi=100)
        fig.patch.set_facecolor(_BG)
        fig.subplots_adjust(left=0.09, right=0.97, top=0.96, bottom=0.13)

        self.canvas = FigureCanvas(fig)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.ax = fig.add_subplot(111)
        self._draw_plot()
        self._setup_cursor()
        layout.addWidget(self.canvas)

        # --- Close button ---
        close_btn = QPushButton("Close")
        close_btn.setFixedWidth(80)
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn, alignment=Qt.AlignRight)

    # ------------------------------------------------------------------
    # Stylesheet
    # ------------------------------------------------------------------

    def _apply_stylesheet(self):
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {_BG};
            }}
            QLabel {{
                background: transparent;
            }}
            QPushButton {{
                background-color: {_BG_CARD};
                color: {_TEXT};
                border: 1px solid {_BORDER};
                border-radius: 6px;
                padding: 6px 16px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {_BORDER};
            }}
        """)

    # ------------------------------------------------------------------
    # Stats header — large values with muted labels underneath
    # ------------------------------------------------------------------

    def _build_stats_header(self, parent_layout, stats):
        row = QHBoxLayout()
        row.setSpacing(32)

        for label_text, value_text in stats:
            cell = QVBoxLayout()
            cell.setSpacing(1)

            val = QLabel(str(value_text))
            val.setStyleSheet(
                f"color: {_TEXT}; font-size: 20px; font-weight: bold;"
            )
            lbl = QLabel(label_text.rstrip(":"))
            lbl.setStyleSheet(f"color: {_TEXT_MUTED}; font-size: 11px;")

            cell.addWidget(val)
            cell.addWidget(lbl)
            row.addLayout(cell)

        row.addStretch()
        parent_layout.addLayout(row)

    # ------------------------------------------------------------------
    # Plot
    # ------------------------------------------------------------------

    def _draw_plot(self):
        ax = self.ax
        ax.set_facecolor(_BG)

        for i, s in enumerate(self._series):
            color = self._colors[i]
            x = np.asarray(s["x"], dtype=float)
            y = np.asarray(s["y"], dtype=float)

            ax.plot(x, y, color=color, linewidth=1.5,
                    label=s["label"], zorder=3)
            ax.fill_between(x, y, alpha=0.12, color=color, zorder=1)

        # Axis chrome
        ax.set_xlabel("Time (hours)", color=_TEXT_MUTED, fontsize=9)
        if self._series:
            ax.set_ylabel(self._series[0]["label"],
                          color=_TEXT_MUTED, fontsize=9)
        ax.tick_params(colors=_TEXT_MUTED, labelsize=8)
        ax.grid(True, color=_GRID, linewidth=0.5)
        for spine in ax.spines.values():
            spine.set_color(_GRID)

        # Legend for multi-series
        if len(self._series) > 1:
            ax.legend(loc="upper right", fontsize=8,
                      facecolor=_BG_CARD, edgecolor=_BORDER,
                      labelcolor=_TEXT)

        # Peak dot on first series
        if self._series:
            s0 = self._series[0]
            y0 = np.asarray(s0["y"], dtype=float)
            x0 = np.asarray(s0["x"], dtype=float)
            if len(y0) > 0:
                pk = int(np.argmax(y0))
                ax.plot(x0[pk], y0[pk], "o",
                        color=self._colors[0], markersize=6,
                        markeredgecolor="white", markeredgewidth=1.5,
                        zorder=5)

    # ------------------------------------------------------------------
    # Interactive hover cursor
    # ------------------------------------------------------------------

    def _setup_cursor(self):
        ax = self.ax

        self._cursor_vline = ax.axvline(
            x=0, color=_CURSOR, linestyle="-", linewidth=0.8,
            visible=False, zorder=6,
        )

        # One dot per series
        self._cursor_dots = []
        for i in range(len(self._series)):
            dot, = ax.plot(
                [], [], "o", color=self._colors[i], markersize=7,
                markeredgecolor="white", markeredgewidth=1.5,
                visible=False, zorder=7,
            )
            self._cursor_dots.append(dot)

        self._cursor_annot = ax.annotate(
            "", xy=(0, 0), xytext=(14, 14),
            textcoords="offset points", fontsize=8, color=_TEXT,
            bbox=dict(facecolor=_BG_CARD, alpha=0.95,
                      edgecolor=_BORDER, boxstyle="round,pad=0.5"),
            visible=False, zorder=8,
        )

        self.canvas.mpl_connect("motion_notify_event", self._on_mouse_move)

    def _on_mouse_move(self, event):
        if event.inaxes is not self.ax or not self._series:
            self._cursor_vline.set_visible(False)
            for dot in self._cursor_dots:
                dot.set_visible(False)
            self._cursor_annot.set_visible(False)
            self.canvas.draw_idle()
            return

        x0 = np.asarray(self._series[0]["x"], dtype=float)
        if len(x0) == 0:
            return

        idx = int(np.argmin(np.abs(x0 - event.xdata)))
        snap_x = x0[idx]

        parts = []
        first_y = None
        for i, s in enumerate(self._series):
            y_arr = np.asarray(s["y"], dtype=float)
            val = y_arr[idx] if idx < len(y_arr) else float("nan")
            parts.append(f"{s['label']}: {val:,.2f}")
            self._cursor_dots[i].set_data([snap_x], [val])
            self._cursor_dots[i].set_visible(True)
            if first_y is None:
                first_y = val

        text = f"Time: {snap_x:.2f} hrs\n" + "\n".join(parts)

        self._cursor_vline.set_xdata([snap_x, snap_x])
        self._cursor_vline.set_visible(True)
        self._cursor_annot.xy = (snap_x, first_y)
        self._cursor_annot.set_text(text)
        self._cursor_annot.set_visible(True)
        self.canvas.draw_idle()
