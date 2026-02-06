"""
FLO-2D Postprocessor QGIS Plugin - Hydrograph popup dialog.

Displays an interactive hydrograph plot and summary statistics for a
floodplain cross section.  Opened via a QgsAction attached to the fpxsec
vector layer.
"""

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
    """Popup dialog showing a hydrograph plot and key statistics."""

    def __init__(self, section_id, hydrograph_df, stats, parent=None):
        """
        Args:
            section_id (int): Floodplain cross-section ID.
            hydrograph_df (pd.DataFrame): Columns 'time' and 'discharge'.
            stats (dict): Keys 'q_max', 'time_max_discharge', 'vol_acft',
                          'wse_max'.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle(f"Hydrograph — Cross Section {section_id}")
        self.setMinimumSize(700, 550)
        self.setAttribute(Qt.WA_DeleteOnClose)

        layout = QVBoxLayout(self)

        # --- Stats panel ---
        stats_box = QGroupBox("Summary Statistics")
        stats_grid = QGridLayout()
        labels = [
            ("Peak Discharge (CFS):", f"{stats.get('q_max', 'N/A'):.2f}"
             if isinstance(stats.get('q_max'), (int, float)) else "N/A"),
            ("Time to Peak (hr):", f"{stats.get('time_max_discharge', 'N/A'):.2f}"
             if isinstance(stats.get('time_max_discharge'), (int, float)) else "N/A"),
            ("Volume (acre-ft):", f"{stats.get('vol_acft', 'N/A'):.2f}"
             if isinstance(stats.get('vol_acft'), (int, float)) else "N/A"),
            ("Max WSE (ft):", f"{stats.get('wse_max', 'N/A'):.2f}"
             if isinstance(stats.get('wse_max'), (int, float)) else "N/A"),
        ]
        for col, (name, value) in enumerate(labels):
            name_lbl = QLabel(f"<b>{name}</b>")
            val_lbl = QLabel(value)
            stats_grid.addWidget(name_lbl, 0, col * 2)
            stats_grid.addWidget(val_lbl, 0, col * 2 + 1)
        stats_box.setLayout(stats_grid)
        layout.addWidget(stats_box)

        # --- Matplotlib canvas ---
        fig = Figure(figsize=(7, 4), dpi=100, tight_layout=True)
        self.canvas = FigureCanvas(fig)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._plot(fig, section_id, hydrograph_df, stats)
        layout.addWidget(self.canvas)

        # --- Navigation toolbar ---
        toolbar = NavigationToolbar(self.canvas, self)
        layout.addWidget(toolbar)

        # --- Close button ---
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn, alignment=Qt.AlignRight)

    # ------------------------------------------------------------------

    @staticmethod
    def _plot(fig, section_id, df, stats):
        """Draw the hydrograph plot matching the PDF report style."""
        ax = fig.add_subplot(111)

        time_col = df.columns[0]  # 'time'
        discharge_col = df.columns[1]  # 'discharge'

        ax.plot(df[time_col], df[discharge_col], color="blue", linewidth=1.0)

        ax.set_title(f"Cross Section {section_id}")
        ax.set_xlabel("Time (hours)")
        ax.set_ylabel("Discharge (cfs)")
        ax.grid(True)

        # Peak annotation
        max_discharge = stats.get("q_max")
        max_time = stats.get("time_max_discharge")
        max_wse = stats.get("wse_max")

        if isinstance(max_time, (int, float)) and isinstance(max_discharge, (int, float)):
            ax.axvline(x=max_time, color="red", linestyle="--", linewidth=0.8)

        # Annotation box (matches PDF style)
        lines = []
        if isinstance(max_discharge, (int, float)):
            lines.append(f"Peak Discharge: {max_discharge:.2f} cfs")
        if isinstance(max_wse, (int, float)):
            lines.append(f"Max WSE: {max_wse:.2f} ft")
        if isinstance(max_time, (int, float)):
            lines.append(f"Time of Peak: {max_time:.2f} hrs")

        if lines:
            ax.text(
                0.05, 0.95, "\n".join(lines),
                ha="left", va="top",
                transform=ax.transAxes, fontsize=8,
                bbox=dict(facecolor="white", alpha=0.6),
            )
