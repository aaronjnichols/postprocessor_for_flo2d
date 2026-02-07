"""
FLO-2D Postprocessor QGIS Plugin - Interactive time-series popup dialog.

Displays a configurable plot (1 or 2 series) and summary statistics for any
feature type: floodplain cross sections, hydraulic structures, SWMM junctions,
outfalls, or conduits.
"""

import numpy as np
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QGroupBox,
    QGridLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
)

try:
    from matplotlib.backends.backend_qtagg import (
        FigureCanvasQTAgg as FigureCanvas,
        NavigationToolbar2QT as NavigationToolbar,
    )
except ImportError:
    from matplotlib.backends.backend_qt5agg import (
        FigureCanvasQTAgg as FigureCanvas,
        NavigationToolbar2QT as NavigationToolbar,
    )
from matplotlib.figure import Figure


class HydrographDialog(QDialog):
    """Popup dialog showing a time-series plot and key statistics."""

    def __init__(self, title, series, stats, parent=None):
        """
        Args:
            title (str): Window title (e.g. "Hydrograph — Cross Section 5").
            series (list[dict]): Each dict has keys:
                'x' (array-like) — time values,
                'y' (array-like) — data values,
                'label' (str) — legend label,
                'color' (str) — line color.
            stats (list[tuple]): Each tuple is (label_str, value_str).
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(700, 550)
        self.setAttribute(Qt.WA_DeleteOnClose)

        self._series = series

        layout = QVBoxLayout(self)

        # --- Stats panel ---
        if stats:
            stats_box = QGroupBox("Summary Statistics")
            stats_grid = QGridLayout()
            for col, (name, value) in enumerate(stats):
                name_lbl = QLabel(f"<b>{name}</b>")
                val_lbl = QLabel(str(value))
                stats_grid.addWidget(name_lbl, 0, col * 2)
                stats_grid.addWidget(val_lbl, 0, col * 2 + 1)
            stats_box.setLayout(stats_grid)
            layout.addWidget(stats_box)

        # --- Matplotlib canvas ---
        fig = Figure(figsize=(7, 4), dpi=100, tight_layout=True)
        self.canvas = FigureCanvas(fig)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.ax = fig.add_subplot(111)
        self._plot(series)
        self._setup_cursor()
        layout.addWidget(self.canvas)

        # --- Navigation toolbar ---
        toolbar = NavigationToolbar(self.canvas, self)
        layout.addWidget(toolbar)

        # --- Close button ---
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn, alignment=Qt.AlignRight)

    def _plot(self, series):
        """Draw time-series lines, peak annotation, and optional legend."""
        ax = self.ax

        for s in series:
            ax.plot(s['x'], s['y'], color=s['color'], linewidth=1.0,
                    label=s['label'])

        if series:
            ax.set_xlabel("Time (hours)")
            ax.set_ylabel(series[0]['label'])

        ax.grid(True)

        # Legend when multiple series
        if len(series) > 1:
            ax.legend(loc="upper right", fontsize=8)

        # Peak annotation for the first series
        s0 = series[0]
        y_arr = np.asarray(s0['y'], dtype=float)
        x_arr = np.asarray(s0['x'], dtype=float)
        if len(y_arr) > 0:
            idx_max = int(np.argmax(y_arr))
            peak_y = y_arr[idx_max]
            peak_x = x_arr[idx_max]
            ax.axvline(x=peak_x, color="red", linestyle="--", linewidth=0.8)

            lines = [f"Peak {s0['label']}: {peak_y:.2f}",
                     f"Time of Peak: {peak_x:.2f} hrs"]
            if len(series) > 1:
                s1 = series[1]
                y1_arr = np.asarray(s1['y'], dtype=float)
                idx1 = int(np.argmax(y1_arr))
                lines.append(f"Peak {s1['label']}: {y1_arr[idx1]:.2f}")

            ax.text(
                0.05, 0.95, "\n".join(lines),
                ha="left", va="top",
                transform=ax.transAxes, fontsize=8,
                bbox=dict(facecolor="white", alpha=0.6),
            )

    def _setup_cursor(self):
        """Add interactive cursor that snaps to data and shows values."""
        ax = self.ax
        self._cursor_vline = ax.axvline(x=0, color="gray", linestyle=":",
                                        linewidth=0.8, visible=False)
        self._cursor_annot = ax.annotate(
            "", xy=(0, 0), xytext=(10, 10),
            textcoords="offset points", fontsize=8,
            bbox=dict(facecolor="lightyellow", alpha=0.9, edgecolor="gray"),
            visible=False,
        )
        self.canvas.mpl_connect("motion_notify_event", self._on_mouse_move)

    def _on_mouse_move(self, event):
        """Snap to nearest data point and display values."""
        if event.inaxes is not self.ax or not self._series:
            self._cursor_vline.set_visible(False)
            self._cursor_annot.set_visible(False)
            self.canvas.draw_idle()
            return

        mouse_x = event.xdata
        s0 = self._series[0]
        x_arr = np.asarray(s0['x'], dtype=float)
        if len(x_arr) == 0:
            return

        idx = int(np.argmin(np.abs(x_arr - mouse_x)))
        snap_x = x_arr[idx]

        parts = []
        snap_y = None
        for s in self._series:
            y_arr = np.asarray(s['y'], dtype=float)
            val = y_arr[idx] if idx < len(y_arr) else float('nan')
            parts.append(f"{s['label']}: {val:.2f}")
            if snap_y is None:
                snap_y = val

        text = f"Time: {snap_x:.2f} hrs\n" + "\n".join(parts)

        self._cursor_vline.set_xdata([snap_x, snap_x])
        self._cursor_vline.set_visible(True)
        self._cursor_annot.xy = (snap_x, snap_y)
        self._cursor_annot.set_text(text)
        self._cursor_annot.set_visible(True)
        self.canvas.draw_idle()
